import re
from typing import Any, Dict, List, Optional

# Configurable chunking constants
TARGET_CHUNK_WORDS: int = 1000
MAX_CHUNK_WORDS: int = 1500
OVERLAP_WORDS: int = 150
MIN_CHUNK_WORDS: int = 80


def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into sentences using regex boundary detection.
    Preserves punctuation with each sentence.
    """
    sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])')
    sentences = sentence_pattern.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def get_overlap_text(text: str, target_overlap_words: int = OVERLAP_WORDS) -> str:
    """
    Extracts approximately `target_overlap_words` from the tail of `text`,
    aligned to sentence boundaries where possible.
    """
    words = text.split()
    if len(words) <= target_overlap_words:
        return ""

    sentences = split_into_sentences(text)
    if len(sentences) <= 1:
        # Fallback to word slicing if single giant sentence
        return " ".join(words[-target_overlap_words:])

    overlap_sentences: List[str] = []
    accumulated_words = 0

    for sent in reversed(sentences):
        sent_word_count = len(sent.split())
        if accumulated_words + sent_word_count > (target_overlap_words * 1.3) and overlap_sentences:
            break
        overlap_sentences.insert(0, sent)
        accumulated_words += sent_word_count
        if accumulated_words >= target_overlap_words:
            break

    return " ".join(overlap_sentences)


def chunk_pages(
    pages: List[Dict[str, Any]],
    headings: Optional[List[Dict[str, Any]]] = None,
    target_words: int = TARGET_CHUNK_WORDS,
    max_words: int = MAX_CHUNK_WORDS,
    overlap_words: int = OVERLAP_WORDS,
    min_words: int = MIN_CHUNK_WORDS,
) -> List[Dict[str, Any]]:
    """
    Chunks a collection of cleaned pages into intelligent, semantic text blocks.

    Rules:
    - Splits along section/heading boundaries and paragraph boundaries.
    - Maintains target and max chunk sizes.
    - Adds sentence-aligned overlap between sequential chunks in the same section.
    - Accurately tracks `page_start` and `page_end` citations for RAG.
    """
    if not pages:
        return []

    # Map headings to page numbers for fast lookup
    headings_by_page: Dict[int, List[Dict[str, Any]]] = {}
    if headings:
        for h in headings:
            p_num = h["page_number"]
            headings_by_page.setdefault(p_num, []).append(h)

    # Flatten pages into structured paragraph units with metadata
    paragraph_units: List[Dict[str, Any]] = []
    current_section = "General"

    for page in pages:
        p_num = page["page_number"]
        page_text = page.get("text", "").strip()
        if not page_text:
            continue

        # Check for new heading on this page
        if p_num in headings_by_page:
            # Pick the highest level heading on this page
            sorted_headings = sorted(headings_by_page[p_num], key=lambda x: x.get("level", 99))
            if sorted_headings:
                current_section = sorted_headings[0]["text"]

        paragraphs = page_text.split("\n\n")
        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue

            words = para_clean.split()
            paragraph_units.append({
                "text": para_clean,
                "page": p_num,
                "section": current_section,
                "word_count": len(words),
            })

    if not paragraph_units:
        return []

    chunks: List[Dict[str, Any]] = []
    chunk_counter = 1

    current_chunk_paragraphs: List[str] = []
    current_chunk_words = 0
    page_start = paragraph_units[0]["page"]
    page_end = paragraph_units[0]["page"]
    active_section = paragraph_units[0]["section"]

    def finalize_chunk(text_content: str, start_p: int, end_p: int, sec: str):
        nonlocal chunk_counter
        trimmed = text_content.strip()
        if not trimmed:
            return
        w_count = len(trimmed.split())
        c_count = len(trimmed)
        chunks.append({
            "chunk_id": f"chunk_{chunk_counter:03d}",
            "text": trimmed,
            "page_start": start_p,
            "page_end": end_p,
            "section": sec,
            "word_count": w_count,
            "character_count": c_count,
        })
        chunk_counter += 1

    for unit in paragraph_units:
        unit_text = unit["text"]
        unit_words = unit["word_count"]
        unit_page = unit["page"]
        unit_section = unit["section"]

        # If section changed and current chunk has reached minimum size, finalize chunk
        if unit_section != active_section and current_chunk_words >= min_words:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            finalize_chunk(chunk_text, page_start, page_end, active_section)

            # Reset for new section (no overlap across distinct chapters/major sections)
            current_chunk_paragraphs = []
            current_chunk_words = 0
            page_start = unit_page
            active_section = unit_section

        # If a single paragraph is larger than max_words, split it by sentences
        if unit_words > max_words:
            sentences = split_into_sentences(unit_text)
            for sent in sentences:
                sent_words = len(sent.split())
                if current_chunk_words + sent_words > target_words and current_chunk_words >= min_words:
                    chunk_text = "\n\n".join(current_chunk_paragraphs)
                    finalize_chunk(chunk_text, page_start, page_end, active_section)

                    overlap = get_overlap_text(chunk_text, overlap_words)
                    current_chunk_paragraphs = [overlap] if overlap else []
                    current_chunk_words = len(overlap.split()) if overlap else 0
                    page_start = unit_page

                current_chunk_paragraphs.append(sent)
                current_chunk_words += sent_words
                page_end = unit_page
            continue

        # Normal paragraph accumulation
        if current_chunk_words + unit_words > target_words and current_chunk_words >= min_words:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            finalize_chunk(chunk_text, page_start, page_end, active_section)

            # Start next chunk with overlap from the previous chunk
            overlap = get_overlap_text(chunk_text, overlap_words)
            current_chunk_paragraphs = [overlap] if overlap else []
            current_chunk_words = len(overlap.split()) if overlap else 0
            page_start = unit_page

        current_chunk_paragraphs.append(unit_text)
        current_chunk_words += unit_words
        page_end = unit_page

    # Finalize any remaining accumulated content
    if current_chunk_paragraphs:
        chunk_text = "\n\n".join(current_chunk_paragraphs)
        finalize_chunk(chunk_text, page_start, page_end, active_section)

    return chunks
