import json
import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from .llm_client import call_gemini_json, get_gemini_config, LLMKeyMissingError, LLMError

logger = logging.getLogger("lms.ai.generator")


class CourseGenerationError(Exception):
    """Raised when course generation fails or output cannot be validated."""
    pass


# --- Pydantic Data Models ---

class LessonStructure(BaseModel):
    title: str = Field(..., min_length=2, description="Lesson title")
    description: str = Field(..., min_length=5, description="Brief lesson summary/description")
    learning_objective: str = Field(..., min_length=5, description="Measurable learning objective")
    content: str = Field(..., min_length=10, description="Comprehensive explanatory lesson content grounded in source text")
    order_number: int = Field(..., ge=1, description="Sequential position within the module")
    estimated_minutes: int = Field(default=20, ge=1, le=180, description="Estimated completion time in minutes")
    difficulty: Literal["beginner", "intermediate", "advanced"] = Field(
        default="beginner", description="Difficulty level"
    )
    source_pages: List[int] = Field(default_factory=list, description="Original PDF page citations")

    @field_validator("source_pages")
    @classmethod
    def validate_pages(cls, v):
        if not isinstance(v, list):
            return []
        valid_pages = sorted(list(set(int(p) for p in v if isinstance(p, (int, float, str)) and str(p).isdigit() and int(p) > 0)))
        return valid_pages


class ModuleStructure(BaseModel):
    title: str = Field(..., min_length=2, description="Module title")
    description: str = Field(..., min_length=5, description="Module summary and scope")
    order_number: int = Field(..., ge=1, description="Sequential position within the course")
    lessons: List[LessonStructure] = Field(..., min_length=1, description="List of lessons in this module")


class CourseStructure(BaseModel):
    title: str = Field(..., min_length=2, description="Course title")
    description: str = Field(..., min_length=10, description="Comprehensive course description")
    modules: List[ModuleStructure] = Field(..., min_length=1, description="List of modules")


# --- Scalable Batching Utilities ---

def group_chunks_by_section(chunks: List[Dict[str, Any]], max_chunks_per_batch: int = 4) -> List[Dict[str, Any]]:
    """
    Groups chunks hierarchically:
    1. Clusters chunks sharing the same detected section name.
    2. Sub-batches any section cluster exceeding `max_chunks_per_batch` into manageable payloads.
    3. Handles generic/unsectioned chunks gracefully.

    Returns:
        List of batch dictionaries: {"section_title": str, "chunks": List[Dict], "pages": List[int]}
    """
    if not chunks:
        return []

    # Cluster by section name preserving sequential order
    section_clusters: List[Dict[str, Any]] = []
    current_cluster: Optional[Dict[str, Any]] = None

    for chunk in chunks:
        sec_name = chunk.get("section", "General") or "General"
        if not current_cluster or current_cluster["section_title"] != sec_name:
            current_cluster = {
                "section_title": sec_name,
                "chunks": [chunk],
            }
            section_clusters.append(current_cluster)
        else:
            current_cluster["chunks"].append(chunk)

    # Sub-batch large clusters
    batches: List[Dict[str, Any]] = []
    for cluster in section_clusters:
        cluster_chunks = cluster["chunks"]
        sec_title = cluster["section_title"]

        for i in range(0, len(cluster_chunks), max_chunks_per_batch):
            batch_slice = cluster_chunks[i : i + max_chunks_per_batch]
            # Collect unique page citations across this batch
            batch_pages = set()
            for ch in batch_slice:
                p_start = ch.get("page_start", 1)
                p_end = ch.get("page_end", p_start)
                for p in range(p_start, p_end + 1):
                    batch_pages.add(p)

            batch_label = sec_title if len(cluster_chunks) <= max_chunks_per_batch else f"{sec_title} (Part {i // max_chunks_per_batch + 1})"
            batches.append({
                "section_title": batch_label,
                "chunks": batch_slice,
                "pages": sorted(list(batch_pages)),
            })

    return batches


# --- Grounded Offline Generator (Fallback & Testing) ---

def generate_grounded_fallback_course(
    chunks: List[Dict[str, Any]],
    course_title: Optional[str] = None,
) -> CourseStructure:
    """
    Generates a deterministic, strictly validated CourseStructure directly from
    the supplied chunks and section metadata without requiring external LLM API keys.
    """
    if not chunks:
        raise CourseGenerationError("Cannot generate course from empty chunks list.")

    batches = group_chunks_by_section(chunks)
    modules: List[ModuleStructure] = []

    derived_title = course_title
    if not derived_title:
        first_section = batches[0]["section_title"]
        derived_title = first_section if first_section != "General" else "Comprehensive Course"

    for mod_idx, batch in enumerate(batches, start=1):
        sec_name = batch["section_title"]
        batch_chunks = batch["chunks"]
        batch_pages = batch["pages"]

        lessons: List[LessonStructure] = []
        for les_idx, chunk in enumerate(batch_chunks, start=1):
            text = chunk.get("text", "").strip()
            p_start = chunk.get("page_start", 1)
            p_end = chunk.get("page_end", p_start)
            c_pages = list(range(p_start, p_end + 1))

            # Derive concise lesson title and objective from the chunk text
            first_sentence = text.split(".")[0].strip()
            if len(first_sentence) < 5 or len(first_sentence) > 70:
                lesson_title = f"{sec_name} - Core Concept {les_idx}"
            else:
                lesson_title = first_sentence

            objective = f"Understand and apply key principles from {sec_name} (pages {p_start}–{p_end})."
            summary_desc = f"Comprehensive study of concepts covered in {sec_name} with focus on foundational mechanics."

            lessons.append(LessonStructure(
                title=lesson_title,
                description=summary_desc,
                learning_objective=objective,
                content=text if len(text) >= 10 else f"Detailed review and analysis of {lesson_title} based on source materials.",
                order_number=les_idx,
                estimated_minutes=20,
                difficulty="beginner" if les_idx == 1 else "intermediate",
                source_pages=c_pages,
            ))

        modules.append(ModuleStructure(
            title=sec_name if sec_name != "General" else f"Module {mod_idx}: Core Concepts",
            description=f"Detailed educational module covering concepts and topics across pages {batch_pages[0]}–{batch_pages[-1]}.",
            order_number=mod_idx,
            lessons=lessons,
        ))

    course_desc = (
        f"An in-depth, structured curriculum built directly from the uploaded educational material, "
        f"consisting of {len(modules)} modules and {sum(len(m.lessons) for m in modules)} detailed lessons."
    )

    return CourseStructure(
        title=derived_title,
        description=course_desc,
        modules=modules,
    )


# --- LLM Batch Generation ---

def generate_module_from_batch_llm(
    batch: Dict[str, Any],
    module_order: int,
) -> ModuleStructure:
    """
    Calls Google Gemini to generate a single structured module from a batch of chunks.
    """
    sec_title = batch["section_title"]
    batch_chunks = batch["chunks"]
    batch_pages = batch["pages"]

    # Format chunks cleanly for the prompt
    formatted_chunks = []
    for c in batch_chunks:
        formatted_chunks.append(
            f"[Chunk ID: {c.get('chunk_id')}, Pages: {c.get('page_start')}–{c.get('page_end')}]\n{c.get('text', '')}"
        )
    chunks_text = "\n\n---\n\n".join(formatted_chunks)

    system_prompt = (
        "You are an expert curriculum designer. Your task is to design a high-quality educational module "
        "based strictly on the provided textbook excerpts. Do NOT hallucinate or invent concepts not mentioned.\n"
        "Return ONLY a JSON object matching this exact schema:\n"
        "{\n"
        '  "title": "Module Title",\n'
        '  "description": "Module Overview",\n'
        f'  "order_number": {module_order},\n'
        '  "lessons": [\n'
        "    {\n"
        '      "title": "Lesson Title",\n'
        '      "description": "Short description",\n'
        '      "learning_objective": "By the end of this lesson, students will...",\n'
        '      "content": "Detailed educational lesson content grounded in source text",\n'
        '      "order_number": 1,\n'
        '      "estimated_minutes": 20,\n'
        '      "difficulty": "beginner|intermediate|advanced",\n'
        f'      "source_pages": {batch_pages}\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"Section/Topic: {sec_title}\n"
        f"Source Pages: {batch_pages}\n\n"
        f"Textbook Chunks:\n{chunks_text}\n\n"
        "Generate 1 to 3 focused lessons that break down the educational material in these chunks."
    )

    raw_response = call_gemini_json(user_prompt, system_instruction=system_prompt)
    raw_response["order_number"] = module_order
    return ModuleStructure.model_validate(raw_response)


def generate_course_from_chunks(
    chunks: List[Dict[str, Any]],
    course_title: Optional[str] = None,
) -> CourseStructure:
    """
    Main orchestration entrypoint for Phase 3 course generation:
    1. Validates input chunks.
    2. Groups chunks into scalable section batches to handle large textbooks.
    3. If GEMINI_API_KEY is present, executes batch LLM generation and synthesizes course.
    4. If no API key is present, generates a grounded fallback course conforming to schema.
    5. Validates output through Pydantic CourseStructure.
    """
    if not chunks:
        raise CourseGenerationError("No content chunks available for course generation.")

    api_key, model_name = get_gemini_config()

    # Use grounded fallback if no API key is configured or during test mode
    if not api_key or os.getenv("TEST_MODE") == "true":
        logger.info("Using grounded deterministic generator (no API key or test mode).")
        return generate_grounded_fallback_course(chunks, course_title=course_title)

    logger.info("Starting scalable Gemini course generation using model '%s'...", model_name)
    batches = group_chunks_by_section(chunks)

    generated_modules: List[ModuleStructure] = []
    for mod_idx, batch in enumerate(batches, start=1):
        try:
            logger.info("Generating module %d/%d for section: %s", mod_idx, len(batches), batch["section_title"])
            module = generate_module_from_batch_llm(batch, module_order=mod_idx)
            generated_modules.append(module)
        except Exception as exc:
            logger.warning("Gemini batch generation failed for section '%s': %s. Falling back to grounded extraction.", batch["section_title"], exc)
            fallback_course = generate_grounded_fallback_course(batch["chunks"], course_title=batch["section_title"])
            for m in fallback_course.modules:
                m.order_number = mod_idx
                generated_modules.append(m)

    if not generated_modules:
        raise CourseGenerationError("Failed to generate any modules from the supplied chunks.")

    # Derive overall course title and description
    final_title = course_title or generated_modules[0].title
    final_description = (
        f"AI-Generated curriculum covering {len(generated_modules)} modules and "
        f"{sum(len(m.lessons) for m in generated_modules)} lessons, grounded in uploaded educational material."
    )

    course_data = {
        "title": final_title,
        "description": final_description,
        "modules": [m.model_dump() for m in generated_modules],
    }

    try:
        return CourseStructure.model_validate(course_data)
    except Exception as exc:
        raise CourseGenerationError(f"Generated course structure failed Pydantic validation: {exc}") from exc
