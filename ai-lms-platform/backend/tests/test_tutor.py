"""
tests/test_tutor.py - Phase 6 Step 2 Tests: AI Tutor & Grounded RAG Service.

Covers:
- Retrieval of relevant course context for student questions.
- Strict course isolation (zero cross-course contamination).
- Grounded prompt construction containing chunks and page citations.
- Conservative guardrails: unsupported questions refused without calling Gemini.
- Citation structure containing chunk_id, page_start, page_end, section, excerpt, score.
- Gemini success path (mocked, no live key required).
- Gemini failure fallback (deterministic grounded synthesis without crashing).
- Empty/invalid question handling.
- No-context behavior for unindexed courses.
- Deterministic offline fallback answer generation.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from vector.embeddings import EmbeddingEngine
from vector.store import VectorStore, SearchResult
from ai.tutor import (
    ask_tutor,
    build_grounded_tutor_prompt,
    generate_grounded_fallback_answer,
    extract_chunk_excerpt,
    TutorResponse,
    TutorCitation,
    DEFAULT_REFUSAL_MESSAGE,
)
from ai.llm_client import LLMResponseError


@pytest.fixture
def temp_vector_dir(tmp_path: Path) -> Path:
    """Provides an isolated vector storage directory for tutor tests."""
    v_dir = tmp_path / "tutor_vectors"
    v_dir.mkdir(parents=True, exist_ok=True)
    return v_dir


@pytest.fixture
def tutor_vector_store(temp_vector_dir: Path) -> VectorStore:
    """Provides a VectorStore pre-populated with test course chunks."""
    engine = EmbeddingEngine(provider="local")
    store = VectorStore(storage_dir=temp_vector_dir, embedding_engine=engine)

    # Course 101: Computer Science (Data Structures & Algorithms)
    store.add_chunks(
        course_id=101,
        chunks=[
            {
                "chunk_id": "cs_001",
                "text": (
                    "Binary search trees (BST) are node-based binary tree data structures "
                    "where the left subtree contains keys smaller than the node, and the right "
                    "subtree contains keys greater than the node. BST search operations achieve "
                    "O(log n) average time complexity."
                ),
                "page_start": 15,
                "page_end": 17,
                "section": "Binary Search Trees",
            },
            {
                "chunk_id": "cs_002",
                "text": (
                    "Merge sort is a divide-and-conquer algorithm that divides the input array "
                    "into two halves, recursively sorts them, and merges the sorted halves. "
                    "Its worst-case time complexity is O(n log n)."
                ),
                "page_start": 30,
                "page_end": 32,
                "section": "Sorting Algorithms",
            },
        ],
    )

    # Course 202: Biology (Cell Biology)
    store.add_chunks(
        course_id=202,
        chunks=[
            {
                "chunk_id": "bio_001",
                "text": (
                    "Mitochondria are membrane-bound cell organelles that generate most of the "
                    "chemical energy needed to power the biochemical reactions through ATP synthesis. "
                    "They are often referred to as the powerhouse of the cell."
                ),
                "page_start": 5,
                "page_end": 8,
                "section": "Cellular Organelles",
            }
        ],
    )

    # Course 303: Harassment Awareness & Prevention
    store.add_chunks(
        course_id=303,
        chunks=[
            {
                "chunk_id": "chunk_001",
                "text": (
                    "Campus Safety Harassment Awareness & Prevention. All members of the community "
                    "are entitled to a study and work environment free from all forms of harassment."
                ),
                "page_start": 1,
                "page_end": 1,
                "section": "Campus Safety Harassment Awareness & Prevention",
            },
            {
                "chunk_id": "chunk_002",
                "text": (
                    "The policy prohibits all forms of harassment including verbal harassment "
                    "(epithets, derogatory comments, or slurs), physical harassment (unwanted touching, "
                    "blocking movement), and visual harassment (derogatory posters, cartoons, or drawings). "
                    "Sexual harassment is a specific form of harassment that includes unwelcome sexual advances."
                ),
                "page_start": 2,
                "page_end": 2,
                "section": "Types of Harassment",
            },
            {
                "chunk_id": "chunk_003",
                "text": (
                    "Taking Action: If you experience or observe harassment, report it immediately to "
                    "Human Resources or a designated officer. Retaliation against any individual for "
                    "reporting harassment or participating in an investigation is strictly prohibited."
                ),
                "page_start": 3,
                "page_end": 3,
                "section": "Taking Action",
            },
        ],
    )

    return store


# --- Tutor Tests ---

def test_ask_tutor_relevant_question_retrieves_context(tutor_vector_store: VectorStore):
    """1. Relevant question retrieves relevant context chunks in offline mode."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res = ask_tutor(
            course_id=101,
            question="What is the average time complexity of binary search trees?",
            vector_store=tutor_vector_store,
        )

    assert isinstance(res, TutorResponse)
    assert res.is_refusal is False
    assert res.course_id == 101
    assert len(res.citations) > 0

    top_cite = res.citations[0]
    assert top_cite.chunk_id == "cs_001"
    assert top_cite.page_start == 15
    assert top_cite.page_end == 17
    assert top_cite.section == "Binary Search Trees"
    assert "binary search trees" in res.answer.lower()


def test_ask_tutor_course_isolation(tutor_vector_store: VectorStore):
    """2. Course 101 search retrieves only Course 101 chunks; Course 202 only Course 202."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res_cs = ask_tutor(course_id=101, question="binary search tree", vector_store=tutor_vector_store)
        res_bio = ask_tutor(course_id=202, question="mitochondria ATP", vector_store=tutor_vector_store)

    assert res_cs.course_id == 101
    for c in res_cs.citations:
        assert c.chunk_id.startswith("cs_")

    assert res_bio.course_id == 202
    for c in res_bio.citations:
        assert c.chunk_id.startswith("bio_")


def test_no_cross_course_contamination(tutor_vector_store: VectorStore):
    """3. Asking about biology in Course 101 is refused and never returns Course 202 chunks."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res = ask_tutor(
            course_id=101,
            question="Explain mitochondria and ATP cellular synthesis in detail",
            vector_store=tutor_vector_store,
            min_score=0.20,
        )

    # Should be refused because Course 101 has no biology chunks
    assert res.is_refusal is True
    assert len(res.citations) == 0
    assert "cannot find information about this in your course material" in res.answer.lower()


def test_build_grounded_tutor_prompt_contains_context_and_citations():
    """4. build_grounded_tutor_prompt injects chunk text, IDs, pages, and section."""
    chunks = [
        SearchResult(
            chunk_id="chk_42",
            text="Relational databases use ACID transactions.",
            score=0.88,
            page_start=12,
            page_end=14,
            section="Transactions",
            course_id=1,
            metadata={},
        )
    ]

    system_inst, user_prompt = build_grounded_tutor_prompt(
        question="What are ACID transactions?",
        course_id=1,
        chunks=chunks,
    )

    assert "STRICT GROUNDING RULES" in system_inst
    assert "chk_42" in user_prompt
    assert "Pages 12–14" in user_prompt
    assert "Transactions" in user_prompt
    assert "Relational databases use ACID transactions." in user_prompt
    assert "What are ACID transactions?" in user_prompt


def test_unsupported_question_refused_without_calling_gemini(tutor_vector_store: VectorStore):
    """5. Unsupported question is refused immediately without calling Gemini."""
    with patch("ai.tutor.call_gemini_json") as mock_gemini:
        res = ask_tutor(
            course_id=101,
            question="What is the recipe for chocolate chip cookies?",
            vector_store=tutor_vector_store,
            min_score=0.20,
        )

        # Gemini must NEVER be called for unsupported/irrelevant questions
        mock_gemini.assert_not_called()

    assert res.is_refusal is True
    assert res.citations == []
    assert "cannot find information" in res.answer.lower()


def test_citations_contain_page_and_section_metadata(tutor_vector_store: VectorStore):
    """6. Citations contain chunk_id, page numbers, section, excerpt, and score."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res = ask_tutor(
            course_id=101,
            question="divide and conquer merge sort algorithm",
            vector_store=tutor_vector_store,
        )

    assert len(res.citations) > 0
    cite = res.citations[0]
    assert cite.chunk_id == "cs_002"
    assert cite.page_start == 30
    assert cite.page_end == 32
    assert cite.section == "Sorting Algorithms"
    assert len(cite.excerpt) > 10
    assert cite.score > 0.20


def test_gemini_success_path(tutor_vector_store: VectorStore):
    """7. Mocked Gemini returns grounded answer with citations and is_fallback=False."""
    mock_response = {
        "answer": "A binary search tree operates by maintaining sorted order, enabling O(log n) searches.",
        "cannot_answer": False,
    }

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key", "TEST_MODE": "false"}):
        with patch("ai.tutor.call_gemini_json", return_value=mock_response) as mock_gemini:
            res = ask_tutor(
                course_id=101,
                question="How does binary search tree searching work?",
                vector_store=tutor_vector_store,
            )
            mock_gemini.assert_called_once()

    assert res.is_fallback is False
    assert res.is_refusal is False
    assert "binary search tree operates" in res.answer
    assert len(res.citations) > 0
    assert res.citations[0].chunk_id == "cs_001"


def test_gemini_failure_fallback(tutor_vector_store: VectorStore):
    """8. When Gemini fails or times out, tutor provides deterministic grounded fallback."""
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key", "TEST_MODE": "false"}):
        with patch("ai.tutor.call_gemini_json", side_effect=LLMResponseError("HTTP 503 Service Unavailable")):
            res = ask_tutor(
                course_id=101,
                question="Explain merge sort time complexity",
                vector_store=tutor_vector_store,
            )

    # Must NOT crash; should return grounded fallback with citations
    assert res.is_fallback is True
    assert res.is_refusal is False
    assert len(res.citations) > 0
    assert "Sorting Algorithms" in res.answer or "merge sort" in res.answer.lower()
    assert res.citations[0].chunk_id == "cs_002"


def test_empty_or_whitespace_question_handling(tutor_vector_store: VectorStore):
    """9. Empty or whitespace question returns helpful prompt without invoking LLM."""
    with patch("ai.tutor.call_gemini_json") as mock_gemini:
        res1 = ask_tutor(course_id=101, question="", vector_store=tutor_vector_store)
        res2 = ask_tutor(course_id=101, question="   \n\t  ", vector_store=tutor_vector_store)
        mock_gemini.assert_not_called()

    assert res1.is_refusal is True
    assert res2.is_refusal is True
    assert res1.citations == []
    assert res2.citations == []
    assert "ask a specific question" in res1.answer.lower()


def test_no_context_behavior_for_unindexed_course(tutor_vector_store: VectorStore):
    """10. Unindexed course ID returns refusal without crashing or calling Gemini."""
    with patch("ai.tutor.call_gemini_json") as mock_gemini:
        res = ask_tutor(course_id=9999, question="Any question", vector_store=tutor_vector_store)
        mock_gemini.assert_not_called()

    assert res.is_refusal is True
    assert res.citations == []
    assert "cannot find information" in res.answer.lower()


def test_deterministic_fallback_behavior():
    """11. generate_grounded_fallback_answer formats pages and section correctly."""
    chunks = [
        SearchResult(
            chunk_id="chunk_test",
            text="Recursion terminates when the base case is reached. Without a base case, stack overflow occurs.",
            score=0.75,
            page_start=4,
            page_end=4,
            section="Recursion Basics",
            course_id=1,
            metadata={},
        )
    ]

    ans = generate_grounded_fallback_answer("What happens without a base case?", chunks)
    assert "Section 'Recursion Basics'" in ans
    assert "Page 4" in ans
    assert "base case" in ans


def test_excerpt_extraction_cleanliness():
    """12. extract_chunk_excerpt cleans whitespace and ends cleanly."""
    long_text = "Sentence one. Sentence two is very clear. " + ("Extra word " * 40)
    excerpt = extract_chunk_excerpt(long_text, max_chars=80)
    assert len(excerpt) <= 85
    assert not excerpt.startswith(" ")


def test_gemini_cannot_answer_flag(tutor_vector_store: VectorStore):
    """13. When Gemini returns cannot_answer=True, tutor treats it as refusal."""
    mock_response = {
        "answer": "The text does not mention this.",
        "cannot_answer": True,
    }

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key", "TEST_MODE": "false"}):
        with patch("ai.tutor.call_gemini_json", return_value=mock_response):
            res = ask_tutor(
                course_id=101,
                question="What is the color of the author's dog?",
                vector_store=tutor_vector_store,
                min_score=0.01,
            )

    assert res.is_refusal is True
    assert "not contain enough information" in res.answer.lower()


def test_unrelated_question_capital_of_france_refusal(tutor_vector_store: VectorStore):
    """14. Unrelated question 'What is the capital of France?' is refused with empty citations and 0 confidence."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res = ask_tutor(
            course_id=303,
            question="What is the capital of France?",
            vector_store=tutor_vector_store,
            min_score=0.20,
        )

    assert res.is_refusal is True
    assert res.citations == []
    assert res.confidence == 0.0
    assert "cannot find information about this in your course material" in res.answer.lower()


def test_legitimate_question_types_of_harassment_answers_with_citation(tutor_vector_store: VectorStore):
    """15. Legitimate question 'What are the types of harassment?' retrieves chunk_002 and answers with citation."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res = ask_tutor(
            course_id=303,
            question="What are the types of harassment?",
            vector_store=tutor_vector_store,
            min_score=0.20,
        )

    assert res.is_refusal is False
    assert len(res.citations) > 0
    top_citation = res.citations[0]
    assert top_citation.chunk_id == "chunk_002"
    assert top_citation.section == "Types of Harassment"
    assert "verbal harassment" in res.answer.lower() or "types of harassment" in res.answer.lower()


def test_legitimate_question_experience_harassment_answers(tutor_vector_store: VectorStore):
    """16. Legitimate question 'What should I do if I experience harassment?' answers successfully."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        res = ask_tutor(
            course_id=303,
            question="What should I do if I experience harassment?",
            vector_store=tutor_vector_store,
            min_score=0.20,
        )

    assert res.is_refusal is False
    assert len(res.citations) > 0
    assert any(c.chunk_id in ("chunk_002", "chunk_003") for c in res.citations)
    assert "harassment" in res.answer.lower()


def test_fallback_with_no_matching_content_keywords_returns_refusal():
    """17. Fallback generator returns safe refusal when question content keywords match no chunk sentence."""
    chunks = [
        SearchResult(
            chunk_id="chunk_safety",
            text="General workplace guidelines recommend wearing protective headgear in marked areas.",
            score=0.35,
            page_start=1,
            page_end=1,
            section="Safety",
            course_id=303,
            metadata={},
        )
    ]

    # Question with content keywords that do NOT exist in chunk text
    ans = generate_grounded_fallback_answer("What is the capital of France?", chunks)
    assert ans == DEFAULT_REFUSAL_MESSAGE


def test_ask_tutor_converts_fallback_refusal_to_refusal_response(tutor_vector_store: VectorStore):
    """18. When fallback produces refusal message, ask_tutor sets is_refusal=True, citations=[], confidence=0.0."""
    with patch.dict("os.environ", {"TEST_MODE": "true"}):
        # Artificially low min_score allows chunk retrieval, but content keyword mismatch triggers fallback refusal
        res = ask_tutor(
            course_id=303,
            question="What is the capital of France?",
            vector_store=tutor_vector_store,
            min_score=0.01,
        )

    assert res.is_refusal is True
    assert res.citations == []
    assert res.confidence == 0.0
    assert res.answer == DEFAULT_REFUSAL_MESSAGE

