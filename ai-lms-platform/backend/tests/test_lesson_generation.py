import io
import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

try:
    import pymupdf as fitz
except ImportError:
    import fitz  # type: ignore

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from tests.conftest import test_engine, override_get_db
from database.database import Base
from database.models import Course, Module, Lesson, User
from ai.lesson_generator import (
    LessonContent,
    PracticeQuestion,
    generate_grounded_fallback_lesson,
    generate_lesson_content,
    LessonGenerationError,
)
from ai.llm_client import LLMError


def create_test_pdf_bytes() -> bytes:
    """Creates a sample multi-page PDF for testing lesson generation."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "CHAPTER 1: Introduction to Machine Learning\n\n"
        "Machine learning focuses on algorithms that learn patterns from training data.\n"
        "Supervised learning uses labeled training examples consisting of inputs and targets.\n"
        "For example, spam detection models predict whether an incoming email is spam or ham.",
    )
    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "1.1 Neural Networks and Deep Learning\n\n"
        "Artificial neural networks consist of interconnected layers of artificial neurons.\n"
        "Activation functions introduce non-linearities, enabling networks to model complex tasks.\n"
        "A common misconception is that adding more layers always improves model generalization.",
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# --- 1. Schema Validation Tests ---

def test_lesson_content_schema_validation():
    """Verify LessonContent Pydantic model validates conforming data."""
    valid_data = {
        "title": "Supervised Learning Fundamentals",
        "introduction": "An introduction to machine learning principles and labeled training data.",
        "explanation": "Supervised learning utilizes input features mapped to known target values to optimize loss functions.",
        "learning_objectives": [
            "Define supervised learning and labeled datasets.",
            "Understand how model loss is minimized during training.",
        ],
        "key_concepts": ["Supervised Learning", "Labeled Data", "Loss Function"],
        "examples": ["Spam classification: Mapping email text to spam vs non-spam labels."],
        "key_takeaways": ["Supervised learning requires ground-truth labels for training."],
        "common_misconceptions": ["Assuming supervised learning works without labeled data."],
        "practice_questions": [
            {
                "question": "What distinguishes supervised learning from other paradigms?",
                "answer": "The presence of labeled input-output pairs.",
                "explanation": "Supervised learning models explicitly optimize loss based on ground-truth targets.",
            }
        ],
        "estimated_minutes": 25,
        "difficulty": "intermediate",
        "source_pages": [1, 2],
        "is_fallback": False,
    }
    content = LessonContent.model_validate(valid_data)
    assert content.title == "Supervised Learning Fundamentals"
    assert len(content.learning_objectives) == 2
    assert len(content.practice_questions) == 1
    assert content.practice_questions[0].answer == "The presence of labeled input-output pairs."
    assert content.source_pages == [1, 2]


def test_lesson_content_schema_invalid():
    """Verify LessonContent raises ValidationError on invalid data."""
    with pytest.raises(ValidationError):
        LessonContent.model_validate({
            "introduction": "Too short",
            "explanation": "Short",
        })


# --- 2. Grounded Offline Fallback Generator Tests ---

def test_offline_fallback_lesson_generation():
    """Verify deterministic offline fallback produces structured, grounded content."""
    chunks = [
        {
            "chunk_id": "chk_001",
            "page_start": 1,
            "page_end": 1,
            "section": "Machine Learning",
            "text": "Machine learning focuses on algorithms that learn patterns from training data. Supervised learning uses labeled training examples.",
        },
        {
            "chunk_id": "chk_002",
            "page_start": 2,
            "page_end": 2,
            "section": "Neural Networks",
            "text": "Artificial neural networks consist of interconnected layers of artificial neurons. Activation functions introduce non-linearities.",
        },
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Supervised Learning Basics",
        module_title="Foundations",
        course_title="AI Curriculum",
        chunks=chunks,
        estimated_minutes=30,
        difficulty="beginner",
        fallback_pages=[1, 2],
    )

    assert fallback.is_fallback is True
    assert "Supervised Learning Basics" in fallback.introduction
    assert len(fallback.learning_objectives) >= 2
    assert len(fallback.key_concepts) >= 2
    assert len(fallback.practice_questions) >= 2
    assert fallback.source_pages == [1, 2]
    assert fallback.estimated_minutes == 30
    assert fallback.difficulty == "beginner"


# --- 3. API Error Handling Tests ---

def test_generate_nonexistent_lesson_404(client):
    """Verify 404 response when attempting to generate content for a nonexistent lesson."""
    res = client.post("/api/lessons/999999/generate")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_nonexistent_lesson_content_404(client):
    """Verify 404 response when requesting content for a nonexistent lesson."""
    res = client.get("/api/lessons/999999/content")
    assert res.status_code == 404


def test_generate_lesson_missing_pdf(client):
    """Verify 400 response when course has an invalid or missing source PDF file."""
    # Seed user, course, module, lesson manually in DB
    from database.database import get_db
    db = next(override_get_db())

    user = User(name="Teacher Test", email="teacher_test@example.com", role="teacher")
    db.add(user)
    db.flush()

    course = Course(
        title="Orphan Course",
        source_file="nonexistent_pdf_file_12345.pdf",
        teacher_id=user.id,
    )
    db.add(course)
    db.flush()

    module = Module(course_id=course.id, title="Module 1", order_number=1)
    db.add(module)
    db.flush()

    lesson = Lesson(module_id=module.id, title="Lesson 1", order_number=1)
    db.add(lesson)
    db.commit()
    lesson_id = lesson.id
    db.close()

    res = client.post(f"/api/lessons/{lesson_id}/generate")
    assert res.status_code == 400
    assert "was not found in storage" in res.json()["detail"].lower()


def test_lesson_content_not_yet_generated_404(client):
    """Verify 404 response when lesson exists but content has not been generated yet."""
    from database.database import get_db
    db = next(override_get_db())

    user = User(name="Teacher 2", email="teacher2@example.com", role="teacher")
    db.add(user)
    db.flush()

    course = Course(title="Course 2", source_file="some_file.pdf", teacher_id=user.id)
    db.add(course)
    db.flush()

    module = Module(course_id=course.id, title="Module 1", order_number=1)
    db.add(module)
    db.flush()

    lesson = Lesson(module_id=module.id, title="Unprocessed Lesson", order_number=1)
    db.add(lesson)
    db.commit()
    lesson_id = lesson.id
    db.close()

    res = client.get(f"/api/lessons/{lesson_id}/content")
    assert res.status_code == 404
    assert "not been generated" in res.json()["detail"].lower()


# --- 4. End-to-End Lesson Generation & Persistence Tests ---

def test_full_lesson_generation_and_persistence(client):
    """
    Complete flow:
    Upload PDF -> Create course -> Generate curriculum -> Generate lesson content ->
    Verify DB persistence -> Verify GET /api/lessons/{id}/content.
    """
    pdf_bytes = create_test_pdf_bytes()
    filename = "Machine_Learning_Intro.pdf"

    # Step 1: Upload PDF
    up_res = client.post(
        "/api/courses/upload",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    # Step 2: Create course referencing document_id
    c_res = client.post(
        "/api/courses/",
        json={"title": "Introduction to ML", "document_id": doc_id},
    )
    assert c_res.status_code == 201
    course_id = c_res.json()["id"]

    # Step 3: Generate curriculum
    gen_res = client.post(f"/api/courses/{course_id}/generate")
    assert gen_res.status_code == 200

    # Step 4: Fetch generated lessons from database
    db = next(override_get_db())
    course = db.query(Course).filter(Course.id == course_id).first()
    assert course is not None
    assert len(course.modules) > 0
    lesson = course.modules[0].lessons[0]
    lesson_id = lesson.id
    db.close()

    # Step 5: Generate lesson content
    les_gen_res = client.post(f"/api/lessons/{lesson_id}/generate")
    assert les_gen_res.status_code == 200
    data = les_gen_res.json()

    assert data["lesson_id"] == lesson_id
    assert data["title"] == lesson.title
    assert len(data["introduction"]) > 10
    assert len(data["explanation"]) > 20
    assert len(data["learning_objectives"]) >= 1
    assert len(data["key_concepts"]) >= 1
    assert len(data["examples"]) >= 1
    assert len(data["key_takeaways"]) >= 1
    assert len(data["common_misconceptions"]) >= 1
    assert len(data["practice_questions"]) >= 1
    assert data["practice_questions"][0]["question"] != ""
    assert data["practice_questions"][0]["answer"] != ""
    assert isinstance(data["source_pages"], list)
    assert len(data["source_pages"]) > 0

    # Step 6: Verify database persistence
    db = next(override_get_db())
    saved_lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    assert saved_lesson is not None
    assert saved_lesson.content == data["explanation"]
    assert saved_lesson.summary == data["introduction"]
    assert saved_lesson.key_concepts == data["key_concepts"]
    assert saved_lesson.examples == data["examples"]
    assert saved_lesson.key_takeaways == data["key_takeaways"]
    assert saved_lesson.misconceptions == data["common_misconceptions"]
    assert len(saved_lesson.practice_questions) == len(data["practice_questions"])
    db.close()

    # Step 7: Verify GET /api/lessons/{id}/content
    content_res = client.get(f"/api/lessons/{lesson_id}/content")
    assert content_res.status_code == 200
    content_data = content_res.json()
    assert content_data["lesson_id"] == lesson_id
    assert content_data["explanation"] == data["explanation"]
    assert content_data["key_concepts"] == data["key_concepts"]
    assert len(content_data["practice_questions"]) == len(data["practice_questions"])


# --- 5. Regeneration In-Place Test ---

def test_lesson_regeneration_updates_in_place(client):
    """Verify calling generate again updates existing lesson content without duplicating records."""
    pdf_bytes = create_test_pdf_bytes()
    filename = "Regen_Test.pdf"

    up_res = client.post(
        "/api/courses/upload",
        files={"file": (filename, io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = up_res.json()["document_id"]

    c_res = client.post(
        "/api/courses/",
        json={"title": "Regen Test Course", "document_id": doc_id},
    )
    course_id = c_res.json()["id"]

    client.post(f"/api/courses/{course_id}/generate")

    db = next(override_get_db())
    course = db.query(Course).filter(Course.id == course_id).first()
    lesson = course.modules[0].lessons[0]
    lesson_id = lesson.id
    total_lessons_before = db.query(Lesson).count()
    db.close()

    # Generation 1
    res1 = client.post(f"/api/lessons/{lesson_id}/generate")
    assert res1.status_code == 200

    # Generation 2 (Regeneration)
    res2 = client.post(f"/api/lessons/{lesson_id}/generate")
    assert res2.status_code == 200

    # Verify no duplicates were created
    db = next(override_get_db())
    total_lessons_after = db.query(Lesson).count()
    assert total_lessons_before == total_lessons_after
    db.close()


# --- 6. Source Page Preservation Test ---

def test_source_page_preservation_in_lesson_content(client):
    """Verify source_pages are preserved throughout lesson content generation."""
    pdf_bytes = create_test_pdf_bytes()
    up_res = client.post(
        "/api/courses/upload",
        files={"file": ("Pages_Test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = up_res.json()["document_id"]

    c_res = client.post("/api/courses/", json={"title": "Pages Test", "document_id": doc_id})
    course_id = c_res.json()["id"]
    client.post(f"/api/courses/{course_id}/generate")

    db = next(override_get_db())
    lesson = db.query(Lesson).first()
    lesson_id = lesson.id
    db.close()

    gen_res = client.post(f"/api/lessons/{lesson_id}/generate")
    assert gen_res.status_code == 200
    pages = gen_res.json()["source_pages"]
    assert isinstance(pages, list)
    assert len(pages) > 0
    assert all(isinstance(p, int) for p in pages)


# --- 7. Gemini Mocking & Failure Fallback Tests ---

def test_gemini_failure_falls_back_gracefully(client, monkeypatch):
    """Verify system falls back seamlessly to deterministic offline generator if Gemini raises an error."""
    # Configure fake API key to simulate online mode
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("TEST_MODE", raising=False)

    def mock_failing_gemini(*args, **kwargs):
        raise LLMError("Simulated Gemini quota exceeded or network timeout.")

    monkeypatch.setattr("ai.lesson_generator.call_gemini_json", mock_failing_gemini)

    pdf_bytes = create_test_pdf_bytes()
    up_res = client.post(
        "/api/courses/upload",
        files={"file": ("Fallback_Test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = up_res.json()["document_id"]
    c_res = client.post("/api/courses/", json={"title": "Fallback Test", "document_id": doc_id})
    course_id = c_res.json()["id"]
    client.post(f"/api/courses/{course_id}/generate")

    db = next(override_get_db())
    lesson = db.query(Lesson).first()
    lesson_id = lesson.id
    db.close()

    res = client.post(f"/api/lessons/{lesson_id}/generate")
    assert res.status_code == 200
    data = res.json()
    assert data["is_fallback"] is True
    assert len(data["explanation"]) > 20
    assert len(data["key_concepts"]) >= 1


def test_gemini_successful_mock_generation(client, monkeypatch):
    """Verify Gemini JSON response is parsed, validated, and saved with is_fallback=False."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("TEST_MODE", raising=False)

    mock_llm_response = {
        "title": "Mocked AI Lesson",
        "introduction": "This is a mocked AI introduction for testing purposes.",
        "explanation": "Detailed explanation generated by the simulated Gemini model.",
        "learning_objectives": ["Objective 1 from AI", "Objective 2 from AI"],
        "key_concepts": ["Concept Alpha", "Concept Beta"],
        "examples": ["Example instance of Concept Alpha."],
        "key_takeaways": ["Takeaway points regarding the topic."],
        "common_misconceptions": ["Misconception regarding neural layers."],
        "practice_questions": [
            {
                "question": "What is Concept Alpha?",
                "answer": "The primary principle modeled.",
                "explanation": "Directly stated in the prompt text.",
            }
        ],
        "estimated_minutes": 25,
        "difficulty": "intermediate",
        "source_pages": [1],
    }

    def mock_successful_gemini(*args, **kwargs):
        return mock_llm_response

    monkeypatch.setattr("ai.lesson_generator.call_gemini_json", mock_successful_gemini)

    pdf_bytes = create_test_pdf_bytes()
    up_res = client.post(
        "/api/courses/upload",
        files={"file": ("Mock_LLM_Test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    doc_id = up_res.json()["document_id"]
    c_res = client.post("/api/courses/", json={"title": "Mock LLM Course", "document_id": doc_id})
    course_id = c_res.json()["id"]
    client.post(f"/api/courses/{course_id}/generate")

    db = next(override_get_db())
    lesson = db.query(Lesson).first()
    lesson_id = lesson.id
    db.close()

    res = client.post(f"/api/lessons/{lesson_id}/generate")
    assert res.status_code == 200
    data = res.json()
    assert data["is_fallback"] is False
    assert data["explanation"] == "Detailed explanation generated by the simulated Gemini model."
    assert "Concept Alpha" in data["key_concepts"]
    assert len(data["practice_questions"]) == 1
    assert data["practice_questions"][0]["question"] == "What is Concept Alpha?"


# --- 8. Improved Fallback Quality & Determinism Tests ---

def test_fallback_no_generic_placeholders():
    """Verify that improved fallback never outputs generic boilerplate phrases."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 3,
            "page_end": 3,
            "section": "Database Normalization",
            "text": "Normalization organizes data to reduce redundancy and improve data integrity. Third Normal Form requires eliminating transitive dependencies.",
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Third Normal Form",
        module_title="Relational Design",
        course_title="Databases 101",
        chunks=chunks,
        fallback_pages=[3],
    )

    full_output_text = (
        fallback.introduction
        + " " + fallback.explanation
        + " " + " ".join(fallback.learning_objectives)
        + " " + " ".join(fallback.examples)
        + " " + " ".join(fallback.key_takeaways)
        + " " + " ".join(fallback.common_misconceptions)
        + " " + " ".join(q.question + " " + q.answer + " " + q.explanation for q in fallback.practice_questions)
    ).lower()

    # Verify generic placeholders are completely absent
    assert "standard application" not in full_output_text
    assert "structural outcomes and performance metrics" not in full_output_text
    assert "typical domain scenarios" not in full_output_text
    assert "evaluating structural outcomes" not in full_output_text


def test_fallback_linguistic_concept_and_definition_extraction():
    """Verify linguistic copula extraction extracts concepts and definitions directly from text."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 5,
            "page_end": 6,
            "section": "Neural Architectures",
            "text": (
                "Convolutional Neural Networks are specialized architectures for processing grid-structured data. "
                "Backpropagation refers to the automatic differentiation technique used to compute parameter gradients. "
                "Gradient Descent is an optimization algorithm that minimizes the training objective."
            ),
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Convolutional Layers",
        module_title="Deep Learning",
        course_title="Computer Vision",
        chunks=chunks,
        fallback_pages=[5, 6],
    )

    concepts = [c.lower() for c in fallback.key_concepts]
    assert any("convolutional neural networks" in c for c in concepts)
    assert any("backpropagation" in c for c in concepts)
    assert any("gradient descent" in c for c in concepts)

    # Verify practice questions test extracted concepts
    assert len(fallback.practice_questions) >= 2
    assert any("convolutional neural networks" in q.question.lower() or "convolutional neural networks" in q.answer.lower() for q in fallback.practice_questions)
    assert any("pages 5, 6" in q.explanation or "page 5" in q.explanation for q in fallback.practice_questions)


def test_fallback_example_extraction_from_source():
    """Verify explicit source examples are captured without boilerplate."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 10,
            "page_end": 10,
            "section": "Computer Vision",
            "text": (
                "Feature extractors detect visual cues across pixel matrices. "
                "For example, edge detection filters locate rapid transitions in pixel intensity. "
                "Such as Sobel filters used in preliminary image processing pipelines."
            ),
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Edge Detection",
        module_title="Feature Engineering",
        course_title="Vision Systems",
        chunks=chunks,
        fallback_pages=[10],
    )

    assert len(fallback.examples) >= 2
    assert any("edge detection filters" in ex.lower() for ex in fallback.examples)
    assert any("sobel filters" in ex.lower() for ex in fallback.examples)


def test_fallback_determinism():
    """Verify identical source chunks always produce deterministic, stable outputs."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 1,
            "page_end": 2,
            "section": "Algorithms",
            "text": "Binary search is an efficient search algorithm that operates on sorted arrays in logarithmic time.",
        }
    ]

    run1 = generate_grounded_fallback_lesson(
        lesson_title="Binary Search",
        module_title="Search Algorithms",
        course_title="Data Structures",
        chunks=chunks,
        fallback_pages=[1, 2],
    )

    run2 = generate_grounded_fallback_lesson(
        lesson_title="Binary Search",
        module_title="Search Algorithms",
        course_title="Data Structures",
        chunks=chunks,
        fallback_pages=[1, 2],
    )

    assert run1.model_dump() == run2.model_dump()


def test_fallback_filters_heading_fragments_and_gerunds():
    """Verify fallback concept extraction filters out gerunds and heading fragments."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 1,
            "page_end": 1,
            "section": "Defining Sexual Harassment Understanding",
            "text": "Defining Sexual Harassment Understanding the legal framework is important.",
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Workplace Harassment",
        module_title="Compliance",
        course_title="HR Training",
        chunks=chunks,
        fallback_pages=[1],
    )

    concepts = [c.lower() for c in fallback.key_concepts]
    assert "sexual harassment" in concepts
    assert "defining sexual harassment understanding" not in concepts
    assert "defining sexual harassment" not in concepts


def test_fallback_rejects_layout_and_slide_artifacts():
    """Verify fallback completely rejects layout artifacts and presentation noise."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 2,
            "page_end": 2,
            "section": "Our Objectives",
            "text": "Our Objectives What is sexual harassment. Prevention Creating a safe workplace. 02 03 Raise Awareness.",
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Workplace Harassment",
        module_title="Compliance",
        course_title="HR Training",
        chunks=chunks,
        fallback_pages=[2],
    )

    concepts = [c.lower() for c in fallback.key_concepts]
    assert "our objectives what" not in concepts
    assert "prevention creating" not in concepts
    assert "02 03 raise awareness" not in concepts


def test_fallback_cautious_grounded_misconceptions():
    """Verify generated misconceptions are cautious and grounded when no explicit contrast exists."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 3,
            "page_end": 4,
            "section": "Core Concepts",
            "text": "Machine learning focuses on algorithms that learn patterns from training data.",
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Machine Learning Basics",
        module_title="AI Fundamentals",
        course_title="Intro to AI",
        chunks=chunks,
        fallback_pages=[3, 4],
    )

    misc = " ".join(fallback.common_misconceptions).lower()
    assert "assuming that" in misc
    assert "interpreted informally" in misc
    assert "pages 3, 4" in misc


def test_fallback_filters_layout_artifacts_from_explanation_examples_takeaways():
    """Verify that layout numbers, slide headers, and noise are completely excluded from explanation, examples, and takeaways."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 1,
            "page_end": 2,
            "section": "Objectives and Definitions",
            "text": (
                "Our Objectives\n"
                "What we aim to achieve in this session. 02\n"
                "03\n"
                "Raise awareness\n"
                "Promote open dialogue\n"
                "Provide clear guidelines\n"
                "Raise awareness to prevent sexual harassment across the workplace.\n"
                "Promote open dialogue across the entire organization.\n"
                "Provide clear guidelines and supportive resources for reporting misconduct.\n"
                "\n"
                "Defining Sexual Harassment\n"
                "Sexual conduct\n"
                "Sexual advances\n"
                "Requests for favors\n"
                "Unwelcome sexual advances that interfere with work or academic performance.\n"
                "Unwelcome requests for favors that interfere with work or academic performance.\n"
                "Verbal or physical conduct of a sexual nature that creates a hostile environment."
            ),
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Workplace Harassment Prevention",
        module_title="Compliance Training",
        course_title="Organizational Safety",
        chunks=chunks,
        fallback_pages=[1, 2],
    )

    # 1. Explanation must NOT contain layout artifacts
    explanation_lower = fallback.explanation.lower()
    assert "our objectives" not in explanation_lower
    assert "what we aim to achieve" not in explanation_lower
    assert " 02" not in fallback.explanation
    assert " 03" not in fallback.explanation
    assert "\n02\n" not in fallback.explanation
    assert "\n03\n" not in fallback.explanation
    assert "defining sexual harassment" not in explanation_lower

    # Explanation MUST contain meaningful educational sentences
    assert "raise awareness to prevent sexual harassment" in explanation_lower
    assert "unwelcome sexual advances" in explanation_lower
    assert "creates a hostile environment" in explanation_lower

    # 2. Examples must NOT contain layout artifacts
    for ex in fallback.examples:
        ex_lower = ex.lower()
        assert "our objectives" not in ex_lower
        assert "what we aim to achieve" not in ex_lower
        assert "02" not in ex
        assert "03" not in ex
        assert len(ex) > 20

    # 3. Key Takeaways must NOT contain layout artifacts
    for tk in fallback.key_takeaways:
        tk_lower = tk.lower()
        assert "our objectives" not in tk_lower
        assert "what we aim to achieve" not in tk_lower
        assert "02" not in tk
        assert "03" not in tk
        assert len(tk) > 20

    assert fallback.is_fallback is True


def test_fallback_presentation_deck_meaningful_sentences_only():
    """Verify that multi-column slide presentations produce cohesive, educational paragraphs without broken title lines."""
    chunks = [
        {
            "chunk_id": "c1",
            "page_start": 4,
            "page_end": 5,
            "section": "Types of Harassment",
            "text": (
                "Types of Harassment\n"
                "Something for\n"
                "Something\n"
                "Decision Ties\n"
                "Specific Example\n"
                "A direct abuse of power occurs when employment decisions are tied to sexual favors.\n"
                "For example, a supervisor suggesting a promotion in exchange for sexual involvement illustrates quid pro quo.\n"
                "\n"
                "Hostile Environment\n"
                "Off-color behavior\n"
                "Suggestive materials\n"
                "Gratuitous remarks\n"
                "Off-color jokes, teasing, or comments about body parts create an offensive atmosphere.\n"
                "Suggestive pictures, posters, or unwanted digital communications constitute unlawful pressure.\n"
            ),
        }
    ]

    fallback = generate_grounded_fallback_lesson(
        lesson_title="Types of Harassment",
        module_title="Workplace Safety",
        course_title="Ethics",
        chunks=chunks,
        fallback_pages=[4, 5],
    )

    # Layout artifacts dropped
    exp_lower = fallback.explanation.lower()
    assert "types of harassment" not in exp_lower
    assert "something for\nsomething" not in exp_lower
    assert "decision ties" not in exp_lower
    assert "specific example" not in exp_lower
    assert "off-color behavior" not in exp_lower
    assert "suggestive materials" not in exp_lower
    assert "gratuitous remarks" not in exp_lower

    # Substantive sentences present in explanation
    assert "a direct abuse of power" in exp_lower
    assert "off-color jokes" in exp_lower

    # Examples correctly capture genuine illustrative examples
    assert any("promotion in exchange for sexual involvement" in ex.lower() for ex in fallback.examples)

    # Takeaways contain meaningful educational sentences
    assert len(fallback.key_takeaways) >= 2
    for tk in fallback.key_takeaways:
        assert len(tk.split()) >= 4
        assert not tk.isdigit()

