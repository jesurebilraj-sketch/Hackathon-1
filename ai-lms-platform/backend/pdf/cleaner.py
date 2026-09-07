import re
import statistics
from typing import Any, Dict, List, Tuple


def repair_hyphenation(text: str) -> str:
    """
    Repairs words hyphenated across a line break.
    e.g. "intelli-\ngence" -> "intelligence".
    Only joins when the second component begins with a lowercase letter.
    """
    # Pattern matches a word ending with hyphen, newline, optional whitespace, and lowercase continuation
    pattern = re.compile(r'(\b[A-Za-z]+)-\s*\n\s*([a-z]+)', re.MULTILINE)
    return pattern.sub(r'\1\2', text)


def clean_page_numbers_and_artifacts(text: str, current_page: int | None = None) -> str:
    """
    Removes isolated page numbers, headers, and footers.
    e.g. "12", "- 12 -", "Page 12 of 30".
    """
    cleaned_lines = []
    lines = text.split("\n")
    total_lines = len(lines)

    for idx, line in enumerate(lines):
        stripped = line.strip()

        # Check if line is at the very top or bottom of the page (typical header/footer position)
        is_edge = idx <= 2 or idx >= (total_lines - 3)

        # Isolated number: "12", "- 12 -", "[12]", "Page 12"
        if is_edge:
            if re.match(r'^(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?$', stripped, re.IGNORECASE):
                continue
            if re.match(r'^[-–—]\s*\d+\s*[-–—]$', stripped):
                continue
            if current_page is not None and stripped == str(current_page):
                continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def clean_whitespace(text: str) -> str:
    """
    Normalizes excessive whitespace, carriage returns, and blank lines.
    Preserves double newlines (\n\n) as paragraph boundaries.
    """
    # Normalize Windows CRLF to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace tabs and multiple horizontal spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Clean whitespace around punctuation (e.g. "word , word" -> "word, word")
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)

    # Clean space inside parentheses/brackets
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)

    # Clean trailing and leading spaces per line
    lines = [line.strip() for line in text.split("\n")]

    # Normalize paragraph breaks: collapse 3 or more consecutive newlines into 2
    joined = "\n".join(lines)
    joined = re.sub(r'\n{3,}', '\n\n', joined)

    return joined.strip()


def clean_line_wrapping(text: str) -> str:
    """
    Repairs broken line wrapping within a paragraph while preserving true paragraph breaks (\n\n).
    """
    paragraphs = text.split("\n\n")
    cleaned_paragraphs = []

    for para in paragraphs:
        lines = para.split("\n")
        if not lines:
            continue

        merged_para = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # If current paragraph has previous lines, determine if soft wrap or list/heading
            if merged_para:
                prev_line = merged_para[-1]
                # If current line starts with list bullet or number pattern, keep on new line
                if re.match(r'^(?:[•\-\*]|\d+[\.\)])\s+', stripped):
                    merged_para.append(stripped)
                # If previous line ends with a colon, keep current line separate
                elif prev_line.endswith(":"):
                    merged_para.append(stripped)
                # If current line is an isolated number or slide artifact, keep on new line
                elif re.match(r'^\d+$', stripped) or re.match(r'^\d+\s+\d+$', stripped):
                    merged_para.append(stripped)
                # If current line is a short unpunctuated heading/label, keep on new line
                elif len(stripped) < 40 and not stripped.endswith(('.', ',', ';', '-', '?', '!')) and stripped[0].isupper():
                    merged_para.append(stripped)
                # Prevent merging short, unpunctuated layout artifacts
                elif len(prev_line) < 60 and not prev_line.endswith(('.', ',', ';', '-', '?', '!')) and (stripped[0].isupper() or stripped.isdigit()):
                    merged_para.append(stripped)
                else:
                    # Soft wrap: merge with single space
                    merged_para[-1] = f"{prev_line} {stripped}"
            else:
                merged_para.append(stripped)

        if merged_para:
            cleaned_paragraphs.append("\n".join(merged_para))

    return "\n\n".join(cleaned_paragraphs)


def clean_text(raw_text: str, page_number: int | None = None) -> str:
    """
    Full deterministic cleaning pipeline for an extracted page of text.
    """
    if not raw_text:
        return ""

    # Step 1: Repair hyphenated words split across lines
    text = repair_hyphenation(raw_text)

    # Step 2: Remove isolated page numbers and artifacts
    text = clean_page_numbers_and_artifacts(text, current_page=page_number)

    # Step 3: Repair soft line wraps within paragraphs
    text = clean_line_wrapping(text)

    # Step 4: Clean whitespace and normalize spacing
    text = clean_whitespace(text)

    return text


# --- Heading & Structure Detection ---

# Regex patterns for common educational headings
CHAPTER_PATTERN = re.compile(r'^(?:chapter|module|unit|part)\s+\d+[:\.\s\-–—]?', re.IGNORECASE)
NUMBERED_HEADING_PATTERN = re.compile(r'^(?:\d+\.){1,4}\s+[A-Za-z]')
MAJOR_NUMBERED_PATTERN = re.compile(r'^\d+\.\s+[A-Z]')
APPENDIX_PATTERN = re.compile(r'^(?:appendix|glossary|index|bibliography|references)\b', re.IGNORECASE)


def detect_headings_from_blocks(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detects structural headings across document pages using font size heuristics,
    numbered patterns, and capitalization rules.

    Returns:
        List of dicts: {"page_number": int, "text": str, "level": int}
    """
    headings: List[Dict[str, Any]] = []

    # Collect all font sizes across all blocks to find median body font size
    all_font_sizes = []
    for page in pages:
        for block in page.get("blocks", []):
            size = block.get("max_font_size", 0.0)
            if size > 0:
                all_font_sizes.append(size)

    median_font_size = statistics.median(all_font_sizes) if all_font_sizes else 10.0

    for page in pages:
        page_num = page["page_number"]

        for block in page.get("blocks", []):
            text = block.get("text", "").strip()
            font_size = block.get("max_font_size", 0.0)

            # Headings are generally short lines (rarely over 120 characters)
            if not text or len(text) > 140:
                continue

            # Must not end with period, question mark, or comma (unless it's a chapter title)
            if text.endswith((".", ",", ";")) and not NUMBERED_HEADING_PATTERN.match(text):
                continue

            level = None

            # Pattern 1: Chapter / Module / Major section
            if CHAPTER_PATTERN.match(text) or APPENDIX_PATTERN.match(text):
                level = 1

            # Pattern 2: Major Numbered: "1. Introduction"
            elif MAJOR_NUMBERED_PATTERN.match(text):
                level = 1

            # Pattern 3: Sub-sections: "1.1 Operating Systems", "2.3.1 Memory"
            elif NUMBERED_HEADING_PATTERN.match(text):
                parts = text.split()[0].rstrip(".").split(".")
                depth = len([p for p in parts if p.isdigit()])
                level = min(depth, 3)

            # Pattern 4: Font Size Heuristic (if font size is notably larger than median)
            elif font_size >= (median_font_size * 1.35):
                level = 1
            elif font_size >= (median_font_size * 1.18):
                level = 2
            # Pattern 5: ALL CAPS short line with Title Case or prominent spacing
            elif text.isupper() and len(text) < 60 and len(text.split()) >= 1:
                level = 1

            if level is not None:
                # Clean up heading text
                cleaned_heading = re.sub(r'\s+', ' ', text).strip()
                headings.append({
                    "page_number": page_num,
                    "text": cleaned_heading,
                    "level": level,
                })

    return headings
