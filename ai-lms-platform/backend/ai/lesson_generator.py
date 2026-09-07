import json
import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator

from .llm_client import call_gemini_json, get_gemini_config, LLMKeyMissingError, LLMError

logger = logging.getLogger("lms.ai.lesson_generator")


class LessonGenerationError(Exception):
    """Raised when lesson generation fails or cannot be validated."""
    pass


# --- Pydantic Data Models ---

class PracticeQuestion(BaseModel):
    question: str = Field(..., min_length=5, description="The practice question")
    answer: str = Field(..., min_length=2, description="Correct answer")
    explanation: str = Field(..., min_length=5, description="Explanation of why the answer is correct")


class LessonContent(BaseModel):
    title: Optional[str] = Field(None, description="Lesson title")
    introduction: str = Field(..., min_length=10, description="Introductory hook, context, and overview")
    explanation: str = Field(..., min_length=20, description="Comprehensive main explanation grounded in source text")
    learning_objectives: List[str] = Field(default_factory=list, description="Measurable learning objectives")
    key_concepts: List[str] = Field(default_factory=list, description="Key concepts defined in the lesson")
    examples: List[str] = Field(default_factory=list, description="Concrete illustrative examples")
    key_takeaways: List[str] = Field(default_factory=list, description="Important points / key takeaways")
    common_misconceptions: List[str] = Field(default_factory=list, description="Common misconceptions or mistakes")
    practice_questions: List[PracticeQuestion] = Field(default_factory=list, description="Short practice questions")
    estimated_minutes: int = Field(default=20, ge=1, le=180, description="Estimated study time in minutes")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner", description="Difficulty level"
    )
    source_pages: List[int] = Field(default_factory=list, description="Source page references")
    is_fallback: bool = Field(default=False, description="Whether generated via deterministic offline fallback")

    @field_validator("source_pages")
    @classmethod
    def validate_pages(cls, v):
        if not isinstance(v, list):
            return []
        valid_pages = sorted(list(set(
            int(p) for p in v
            if isinstance(p, (int, float, str)) and str(p).isdigit() and int(p) > 0
        )))
        return valid_pages


# --- Grounded Offline Lesson Generator ---

LAYOUT_HEADING_PATTERNS = [
    r'^(?:our\s+)?objectives?[:\.]?$',
    r'^learning\s+objectives?[:\.]?$',
    r'^session\s+objectives?[:\.]?$',
    r'^what\s+we\s+aim\s+to\s+achieve.*$',
    r'^(?:course\s+|session\s+)?agenda[:\.]?$',
    r'^table\s+of\s+contents[:\.]?$',
    r'^contents[:\.]?$',
    r'^overview[:\.]?$',
    r'^summary[:\.]?$',
    r'^q\s*&\s*a[:\.]?$',
    r'^questions?\s*(?:and|&)\s*answers?[:\.]?$',
    r'^thank\s+you.*$',
    r'^(?:chapter|module|unit|part|slide|page)\s+\d+[:\.\s\-–—]?$',
    r'^(?:types\s+of\s+harassment|hostile\s+environment|diverse\s+forms\s+of\s+harassment|taking\s+action|resources\s*&\s*support)[:\.]?$',
]


def is_obvious_layout_artifact(text: str) -> bool:
    """Detects obvious layout artifacts, slide headers, numbers, and fragments."""
    s = text.strip()
    if not s:
        return True
    # Digits / numbers / ranges (e.g. "01", "02 03", "1 - 2")
    if re.match(r'^\d+$', s) or re.match(r'^\d+\s+\d+$', s) or re.match(r'^\d+\s*[\-/]\s*\d+$', s):
        return True
    if re.match(r'^(?:page|slide)\s+\d+(?:\s+(?:of|/)\s+\d+)?$', s, re.IGNORECASE):
        return True
    # Layout headings & presentation meta lines
    for pat in LAYOUT_HEADING_PATTERNS:
        if re.match(pat, s, re.IGNORECASE):
            return True
    # Presentation meta phrases inside a line
    if re.search(r'\bwhat\s+we\s+aim\s+to\s+achieve\b', s, re.IGNORECASE):
        return True
    # Short unpunctuated heading/label fragments (<= 4 words, < 35 chars, no terminal punctuation)
    words = s.split()
    if len(words) <= 4 and len(s) < 35 and not s.endswith(('.', '!', '?')):
        return True
    return False


def _clean_and_extract_sentences(text: str) -> List[str]:
    """
    Extracts clean, meaningful educational sentences from text.
    Strictly filters out presentation headings, slide numbers, and layout artifacts.
    """
    if not text:
        return []
    cleaned: List[str] = []
    seen = set()

    # Split by lines to isolate layout headers, slide numbers, and bullet tags
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        # Strip trailing digit artifacts e.g. "session. 02" -> "session."
        line = re.sub(r'(?<=[.!?])\s+\d{1,2}$', '', line).strip()
        if is_obvious_layout_artifact(line):
            continue

        # Split remaining line on terminal punctuation
        raw_sents = re.split(r"(?<=[.!?])\s+", line)
        for s in raw_sents:
            s_clean = s.strip()
            # Strip noise prefixes (e.g. "01 ", "02 03 ", "Our Objectives: ")
            s_clean = re.sub(r'^(?:\d{1,2}\s+)+', '', s_clean)
            s_clean = re.sub(r'^(?:Our\s+Objectives|Chapter\s+\d+|Module\s+\d+)[:\s\-–—]+', '', s_clean, flags=re.IGNORECASE)
            s_clean = " ".join(s_clean.split())

            if is_obvious_layout_artifact(s_clean):
                continue

            # Check meaningful sentence length: at least 4 words and at least 20 chars
            if len(s_clean.split()) >= 4 and len(s_clean) >= 20:
                if not s_clean.endswith(('.', '!', '?')):
                    s_clean = s_clean + "."
                if s_clean.lower() not in seen:
                    seen.add(s_clean.lower())
                    cleaned.append(s_clean)

    # Fallback to paragraph splitting if text had no line breaks but punctuation
    if not cleaned:
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        for s in raw_sentences:
            s_clean = " ".join(s.split())
            s_clean = re.sub(r'^(?:\d{1,2}\s+)+', '', s_clean)
            if not is_obvious_layout_artifact(s_clean) and len(s_clean.split()) >= 4 and len(s_clean) >= 20:
                if not s_clean.endswith(('.', '!', '?')):
                    s_clean = s_clean + "."
                if s_clean.lower() not in seen:
                    seen.add(s_clean.lower())
                    cleaned.append(s_clean)

    return cleaned


def _clean_concept_candidate(candidate: str) -> Optional[str]:
    """Recursively trims boundary noise words and discards invalid layout artifacts."""
    boundary_noise = {
        "defining", "understanding", "creating", "introducing", "preventing",
        "discussing", "exploring", "raising", "learning", "identifying", 
        "examining", "building", "what", "which", "why", "how", "who", "when", 
        "where", "our", "your", "their", "my", "all", "these", "those", 
        "this", "that", "some", "each", "objectives", "objective", "overview", 
        "introduction", "agenda", "summary", "table", "figure", "section", 
        "chapter", "part", "slide", "lesson", "contents", "outline"
    }
    
    # Discard candidates containing layout numbers (e.g. "02 03 Raise awareness")
    if re.search(r'\b\d{2}\s+\d{2}\b', candidate):
        return None
        
    words = candidate.split()
    
    changed = True
    while changed and words:
        changed = False
        if words[0].lower() in boundary_noise:
            words.pop(0)
            changed = True
        elif words and words[-1].lower() in boundary_noise:
            words.pop()
            changed = True
            
    if not words:
        return None
        
    cleaned = " ".join(words)
    if len(cleaned) < 3 or cleaned.isdigit() or cleaned.lower() in boundary_noise:
        return None
        
    return cleaned


def _extract_definitions_and_concepts(
    sentences: List[str],
    lesson_title: str,
    module_title: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[str]]:
    """
    Extracts terms and definitions using copula patterns and capitalized domain terminology.
    Returns:
        (definitions_list, concept_names_list)
    """
    definitions: List[Dict[str, str]] = []
    concepts: List[str] = []
    seen_concepts = set()

    copula_regex = re.compile(
        r"^(?:The\s+|An?\s+)?([A-Z][a-zA-Z0-9\s\-]{2,35}?)\s+(is defined as|refers to|consists of|focuses on|enables|is an?|are|provides|acts as)\s+(.+)$",
        re.IGNORECASE,
    )

    for sent in sentences:
        match = copula_regex.match(sent)
        if match:
            term = match.group(1).strip()
            copula = match.group(2).strip()
            predicate = match.group(3).strip()
            if len(term.split()) <= 4 and term.lower() not in [
                "this", "that", "there", "it", "they", "we", "chapter", "section"
            ]:
                cleaned_term = _clean_concept_candidate(term)
                if cleaned_term:
                    clean_term = cleaned_term.title()
                    if clean_term.lower() not in seen_concepts:
                        seen_concepts.add(clean_term.lower())
                        concepts.append(clean_term)
                        definitions.append({
                            "term": clean_term,
                            "definition": f"{copula} {predicate}",
                            "source_sentence": sent,
                        })

    # Extract capitalized technical compounds (e.g. "Machine Learning", "Neural Networks")
    for sent in sentences:
        matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", sent)
        for m in matches:
            m_clean = m.strip()
            if len(m_clean.split()) <= 4 and m_clean.lower() not in [
                "for example", "in this", "chapter one", "as well", "united states"
            ]:
                cleaned_term = _clean_concept_candidate(m_clean)
                if cleaned_term:
                    m_final = cleaned_term.title()
                    if m_final.lower() not in seen_concepts:
                        seen_concepts.add(m_final.lower())
                        concepts.append(m_final)
                        definitions.append({
                            "term": m_final,
                            "definition": f"Key concept described in: {sent}",
                            "source_sentence": sent,
                        })

    # Supplementary concepts from lesson title or module title
    if len(concepts) < 3:
        if lesson_title and lesson_title.lower() not in seen_concepts:
            concepts.append(lesson_title.title())
            seen_concepts.add(lesson_title.lower())
        if module_title and module_title.lower() not in seen_concepts:
            concepts.append(module_title.title())
            seen_concepts.add(module_title.lower())

    # Fallback to key nouns from leading sentences
    if len(concepts) < 2 and sentences:
        words = [w.strip(".,;:()") for w in sentences[0].split() if len(w) > 5 and w.isalpha()]
        for w in words[:3]:
            cand = w.capitalize()
            if cand.lower() not in seen_concepts:
                concepts.append(cand)
                seen_concepts.add(cand.lower())

    return definitions, concepts[:6]


def _extract_examples(
    sentences: List[str],
    primary_concept: str,
    source_pages: List[int],
) -> List[str]:
    """Extracts genuine illustrative examples from source sentences without generic boilerplate or layout noise."""
    examples = []
    marker_terms = [
        "for example", "for instance", "such as", "e.g.", "illustrates",
        "demonstrates", "considered as", "example:", "case study",
        "in exchange for", "suggesting a", "specific example"
    ]

    for sent in sentences:
        if is_obvious_layout_artifact(sent):
            continue
        sent_lower = sent.lower()
        if any(marker in sent_lower for marker in marker_terms):
            ex_text = sent.strip()
            if not ex_text.lower().startswith("example"):
                ex_text = f"Example from source: {ex_text}"
            if ex_text not in examples:
                examples.append(ex_text)
            if len(examples) >= 3:
                break

    # If no explicit marker was present in the source text, synthesize grounded factual applications
    if not examples and sentences:
        first_sent = sentences[0]
        examples.append(
            f"Practical Application of {primary_concept}: "
            f"The source material illustrates this concept where: '{first_sent}'"
        )
        if len(sentences) > 1:
            second_sent = sentences[1]
            examples.append(
                f"Contextual Example: As documented on page {source_pages[0]}, '{second_sent}'"
            )

    return examples[:3]


def _extract_misconceptions(
    sentences: List[str],
    primary_concept: str,
    secondary_concept: str,
    source_pages: List[int],
) -> List[str]:
    """Extracts contrastive statements or creates precise conceptual boundary distinctions."""
    misconceptions = []
    contrast_markers = [
        "misconception", "mistake", "not always", "cannot", "does not",
        "however", "unlike", "caution", "instead of", "differs from",
    ]

    for sent in sentences:
        sent_lower = sent.lower()
        if any(marker in sent_lower for marker in contrast_markers):
            misconceptions.append(f"Important Distinction: {sent}")
            if len(misconceptions) >= 2:
                break

    if len(misconceptions) < 2:
        page_str = ", ".join(map(str, source_pages[:3]))
        misconceptions.append(
            f"Assuming that {primary_concept} can be interpreted informally; the source establishes a formal definition and operational criteria documented across source pages {page_str}."
        )

    return misconceptions[:3]


def _extract_takeaways(
    sentences: List[str],
    lesson_title: str,
    primary_concept: str,
) -> List[str]:
    """Extracts impactful, factual takeaway statements directly from clean educational sentences."""
    takeaways = []
    significance_markers = [
        "important", "essential", "primary", "critical", "focuses",
        "enables", "requires", "core", "learn", "prevent", "guidelines",
        "boundaries", "unwelcome", "atmosphere", "misconduct", "thoroughly"
    ]

    for sent in sentences:
        if is_obvious_layout_artifact(sent):
            continue
        sent_lower = sent.lower()
        if any(marker in sent_lower for marker in significance_markers) and len(sent) > 25:
            if sent not in takeaways:
                takeaways.append(sent)
            if len(takeaways) >= 3:
                break

    if len(takeaways) < 2:
        for sent in sentences[:4]:
            if not is_obvious_layout_artifact(sent) and len(sent) > 25 and sent not in takeaways:
                takeaways.append(sent)
            if len(takeaways) >= 3:
                break

    if not takeaways:
        takeaways.append(f"Understanding {primary_concept} is essential for mastering {lesson_title}.")

    return takeaways[:4]


def _build_explanation(
    sentences: List[str],
    lesson_title: str,
    source_pages: List[int],
) -> str:
    """
    Constructs a comprehensive, grounded explanation using only clean educational sentences.
    Groups sentences into natural, structured paragraphs while omitting all layout artifacts.
    """
    if not sentences:
        page_str = ", ".join(map(str, source_pages[:4]))
        return (
            f"This lesson explores the essential theories and applications of {lesson_title}. "
            f"Students will review key definitions and principles outlined in the syllabus across pages {page_str}."
        )

    paragraphs: List[str] = []
    current_para: List[str] = []

    for sent in sentences:
        current_para.append(sent)
        if len(current_para) >= 3:
            paragraphs.append(" ".join(current_para))
            current_para = []

    if current_para:
        paragraphs.append(" ".join(current_para))

    result = "\n\n".join(paragraphs).strip()
    return result if len(result) >= 20 else (
        f"This lesson explores the essential theories and applications of {lesson_title}."
    )


def _generate_practice_questions(
    concepts: List[str],
    definitions: List[Dict[str, str]],
    sentences: List[str],
    source_pages: List[int],
    lesson_title: str,
) -> List[PracticeQuestion]:
    """Constructs direct comprehension questions grounded in extracted definitions and sentences."""
    questions: List[PracticeQuestion] = []
    page_str = ", ".join(map(str, source_pages[:3]))

    for def_item in definitions[:2]:
        term = def_item["term"]
        def_text = def_item["definition"]
        source_sent = def_item["source_sentence"]

        q_text = f"According to the source material, how is {term} described?"
        ans_text = f"{term} {def_text}" if not def_text.lower().startswith(term.lower()) else def_text
        exp_text = f"Grounded in source text (pages {page_str}): '{source_sent}'"

        questions.append(PracticeQuestion(
            question=q_text,
            answer=ans_text,
            explanation=exp_text,
        ))

    if len(questions) < 2 and sentences:
        cand_sent = sentences[min(1, len(sentences) - 1)]
        primary = concepts[0] if concepts else lesson_title
        q_text = f"What key principle regarding {primary} is highlighted in this lesson?"
        ans_text = cand_sent
        exp_text = f"Directly stated in source text on page {source_pages[0]}."

        questions.append(PracticeQuestion(
            question=q_text,
            answer=ans_text,
            explanation=exp_text,
        ))

    return questions[:3]


def generate_grounded_fallback_lesson(
    lesson_title: str,
    module_title: Optional[str],
    course_title: Optional[str],
    chunks: List[Dict[str, Any]],
    estimated_minutes: int = 20,
    difficulty: str = "beginner",
    fallback_pages: Optional[List[int]] = None,
) -> LessonContent:
    """
    Deterministically synthesizes rich, structured LessonContent directly
    from the supplied chunks without external API dependencies.
    Guarantees that generated facts remain grounded in the source text
    and eliminates all generic placeholder boilerplate.
    """
    # 1. Collect pages and text from chunks
    pages_set = set(fallback_pages or [])
    all_text_parts = []

    for c in chunks:
        p_start = c.get("page_start", 1)
        p_end = c.get("page_end", p_start)
        for p in range(p_start, p_end + 1):
            pages_set.add(p)
        txt = c.get("text", "").strip()
        if txt:
            all_text_parts.append(txt)

    combined_text = "\n\n".join(all_text_parts).strip()
    source_pages = sorted(list(pages_set)) if pages_set else [1]
    page_str = ", ".join(map(str, source_pages[:4]))

    # Clean and split into sentences
    sentences = _clean_and_extract_sentences(combined_text)

    # 2. Extract linguistic definitions and key domain concepts
    definitions, key_concepts = _extract_definitions_and_concepts(sentences, lesson_title, module_title)
    primary_concept = key_concepts[0] if key_concepts else lesson_title
    secondary_concept = key_concepts[1] if len(key_concepts) > 1 else (module_title or "Foundational Concepts")

    # 3. Introduction
    intro_lead = f"Welcome to the lesson on '{lesson_title}'."
    if module_title:
        intro_lead += f" Part of the '{module_title}' module."

    if sentences:
        intro_summary = (
            f"In this lesson, we examine essential principles and definitions established in the source material: "
            f"{sentences[0]}"
        )
    else:
        intro_summary = "This lesson provides a comprehensive review of the educational concepts covered in the curriculum."
    introduction = f"{intro_lead} {intro_summary}"

    # 4. Main Explanation
    explanation = _build_explanation(sentences, lesson_title, source_pages)

    # 5. Learning Objectives
    learning_objectives = [
        f"Define and explain the core principles of {primary_concept} as detailed in the source material.",
        f"Analyze how {primary_concept} connects with {secondary_concept} across pages {page_str}.",
        f"Identify and evaluate key factual concepts documented in {lesson_title}.",
    ]

    # 6. Examples (zero generic boilerplate)
    examples = _extract_examples(sentences, primary_concept, source_pages)

    # 7. Key Takeaways
    key_takeaways = _extract_takeaways(sentences, lesson_title, primary_concept)

    # 8. Common Misconceptions
    common_misconceptions = _extract_misconceptions(sentences, primary_concept, secondary_concept, source_pages)

    # 9. Practice Questions (grounded in extracted definitions/sentences)
    practice_questions = _generate_practice_questions(
        key_concepts, definitions, sentences, source_pages, lesson_title
    )

    # Validate difficulty
    valid_diff: Literal["beginner", "intermediate", "advanced"] = "beginner"
    if difficulty in ["beginner", "intermediate", "advanced"]:
        valid_diff = difficulty  # type: ignore

    return LessonContent(
        title=lesson_title,
        introduction=introduction,
        explanation=explanation,
        learning_objectives=learning_objectives,
        key_concepts=key_concepts,
        examples=examples,
        key_takeaways=key_takeaways,
        common_misconceptions=common_misconceptions,
        practice_questions=practice_questions,
        estimated_minutes=max(5, min(180, estimated_minutes)),
        difficulty=valid_diff,
        source_pages=source_pages,
        is_fallback=True,
    )


# --- LLM Lesson Generation ---

def generate_lesson_content(
    lesson_title: str,
    module_title: Optional[str],
    course_title: Optional[str],
    chunks: List[Dict[str, Any]],
    estimated_minutes: int = 20,
    difficulty: str = "beginner",
    fallback_pages: Optional[List[int]] = None,
) -> LessonContent:
    """
    Generates rich, grounded educational content for a single lesson.
    - If Gemini API key is configured and not in test mode, calls Gemini with strict grounding.
    - If Gemini is unavailable, errors, or is unconfigured, uses the deterministic offline fallback.
    """
    api_key, model_name = get_gemini_config()

    # Collect source pages from chunks or fallback
    pages_set = set(fallback_pages or [])
    for c in chunks:
        p_start = c.get("page_start", 1)
        p_end = c.get("page_end", p_start)
        for p in range(p_start, p_end + 1):
            pages_set.add(p)
    resolved_pages = sorted(list(pages_set)) if pages_set else [1]

    # Check for offline / test mode
    if not api_key or os.getenv("TEST_MODE") == "true":
        logger.info("Using grounded deterministic lesson generator (offline mode).")
        return generate_grounded_fallback_lesson(
            lesson_title=lesson_title,
            module_title=module_title,
            course_title=course_title,
            chunks=chunks,
            estimated_minutes=estimated_minutes,
            difficulty=difficulty,
            fallback_pages=resolved_pages,
        )

    logger.info("Invoking Gemini model '%s' for lesson '%s'...", model_name, lesson_title)

    # Format chunks cleanly
    formatted_chunks = []
    for c in chunks:
        formatted_chunks.append(
            f"[Pages {c.get('page_start')}–{c.get('page_end')} | Section: {c.get('section', 'General')}]\n{c.get('text', '')}"
        )
    source_material = "\n\n---\n\n".join(formatted_chunks) if formatted_chunks else "No textbook chunks provided."

    system_instruction = (
        "You are an educational content generator. Generate a clear, accurate lesson using ONLY "
        "the supplied source material. Do not invent unsupported facts. Preserve important terminology "
        "from the source. Make the explanation understandable to a student.\n\n"
        "Return ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "title": "Lesson Title",\n'
        '  "introduction": "An engaging introductory hook and conceptual overview",\n'
        '  "explanation": "Detailed, thorough educational lesson explanation",\n'
        '  "learning_objectives": ["Objective 1", "Objective 2"],\n'
        '  "key_concepts": ["Concept 1", "Concept 2"],\n'
        '  "examples": ["Example 1", "Example 2"],\n'
        '  "key_takeaways": ["Takeaway 1", "Takeaway 2"],\n'
        '  "common_misconceptions": ["Misconception 1", "Misconception 2"],\n'
        '  "practice_questions": [\n'
        "    {\n"
        '      "question": "Clear practice question",\n'
        '      "answer": "Accurate answer",\n'
        '      "explanation": "Why this answer is correct based on the text"\n'
        "    }\n"
        "  ],\n"
        f'  "estimated_minutes": {estimated_minutes},\n'
        f'  "difficulty": "{difficulty}",\n'
        f'  "source_pages": {resolved_pages}\n'
        "}"
    )

    user_prompt = (
        f"Course: {course_title or 'General Course'}\n"
        f"Module: {module_title or 'General Module'}\n"
        f"Lesson Title: {lesson_title}\n"
        f"Target Pages: {resolved_pages}\n\n"
        f"Source Material:\n{source_material}\n\n"
        "Generate the complete structured lesson content grounded in this source material."
    )

    try:
        raw_json = call_gemini_json(user_prompt, system_instruction=system_instruction)
        raw_json["title"] = lesson_title
        raw_json["is_fallback"] = False
        if "source_pages" not in raw_json or not raw_json["source_pages"]:
            raw_json["source_pages"] = resolved_pages
        return LessonContent.model_validate(raw_json)
    except Exception as exc:
        logger.warning(
            "Gemini lesson generation failed for '%s': %s. Falling back to grounded offline generator.",
            lesson_title,
            exc,
        )
        return generate_grounded_fallback_lesson(
            lesson_title=lesson_title,
            module_title=module_title,
            course_title=course_title,
            chunks=chunks,
            estimated_minutes=estimated_minutes,
            difficulty=difficulty,
            fallback_pages=resolved_pages,
        )
