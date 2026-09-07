import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Course, User, Module, Lesson, Enrollment
from pdf import process_pdf, PDFExtractionError
from storage import register_uploaded_document, resolve_source_pdf, UPLOAD_DIR

router = APIRouter(prefix="/api/courses", tags=["Courses"])

# Storage configuration
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit


class ChunkPreview(BaseModel):
    chunk_id: str
    page_start: int
    page_end: int
    section: str
    word_count: int
    character_count: int


class ProcessedPDFResponse(BaseModel):
    success: bool = True
    document_id: str
    filename: str
    stored_filename: str
    pages: int
    characters: int
    words: int
    chunks: int
    sections_detected: int = 0
    processing_time: float
    chunks_preview: Optional[List[ChunkPreview]] = None


class CourseCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    document_id: Optional[str] = None
    source_file: Optional[str] = None
    teacher_id: Optional[int] = None


def get_or_create_default_teacher(db: Session) -> User:
    teacher = db.query(User).filter(User.role == "teacher").first()
    if not teacher:
        teacher = User(name="Default Instructor", email="instructor@lms.local", role="teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
    return teacher


@router.get("/", summary="List all courses")
def list_courses(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Course)
    if category:
        query = query.filter(Course.category == category)
    courses = query.all()
    
    return {
        "count": len(courses),
        "courses": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "category": c.category,
                "imageUrl": c.image_url,
                "teacher_id": c.teacher_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in courses
        ],
    }


@router.post("/", summary="Create a new course", status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreateRequest, db: Session = Depends(get_db)):
    teacher_id = payload.teacher_id
    if not teacher_id:
        teacher = get_or_create_default_teacher(db)
        teacher_id = teacher.id
    else:
        teacher = db.query(User).filter(User.id == teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail=f"Teacher with id {teacher_id} not found.")

    final_source_file = None

    # Priority 1: Resolve document_id if provided
    if payload.document_id:
        resolved_name, resolved_path = resolve_source_pdf(payload.document_id)
        if not resolved_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document with id '{payload.document_id}' was not found in storage. Please upload the PDF first.",
            )
        final_source_file = resolved_name

    # Priority 2: Resolve source_file if provided
    elif payload.source_file:
        resolved_name, resolved_path = resolve_source_pdf(payload.source_file)
        if resolved_path:
            final_source_file = resolved_name
        else:
            # Check if file exists directly on disk in UPLOAD_DIR
            direct_path = UPLOAD_DIR / payload.source_file
            if direct_path.exists():
                final_source_file = payload.source_file
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Source PDF file '{payload.source_file}' was not found in storage. Please upload the PDF first.",
                )

    new_course = Course(
        title=payload.title,
        description=payload.description,
        source_file=final_source_file,
        teacher_id=teacher_id,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return {
        "id": new_course.id,
        "title": new_course.title,
        "description": new_course.description,
        "source_file": new_course.source_file,
        "teacher_id": new_course.teacher_id,
        "created_at": new_course.created_at.isoformat() if new_course.created_at else None,
    }


@router.get("/{course_id}", summary="Get course details with modules and lessons")
def get_course_details(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course with id {course_id} not found.")

    modules_data = []
    for mod in course.modules:
        lessons_data = [
            {
                "id": les.id,
                "title": les.title,
                "description": les.summary,
                "learning_objective": les.learning_objective,
                "content": les.content,
                "order_number": les.order_number,
                "estimated_minutes": les.estimated_minutes,
                "difficulty": les.difficulty,
                "source_pages": les.source_pages,
            }
            for les in mod.lessons
        ]
        modules_data.append({
            "id": mod.id,
            "title": mod.title,
            "description": mod.description,
            "order_number": mod.order_number,
            "lessons": lessons_data,
        })

    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "source_file": course.source_file,
        "teacher_id": course.teacher_id,
        "created_at": course.created_at.isoformat() if course.created_at else None,
        "modules": modules_data,
    }

@router.get("/teacher/{teacher_id}", summary="Get all courses created by a specific teacher")
def get_teacher_courses(teacher_id: int, db: Session = Depends(get_db)):
    courses = db.query(Course).filter(Course.teacher_id == teacher_id).all()
    return {
        "count": len(courses),
        "courses": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in courses
        ]
    }

@router.get("/teacher/{teacher_id}/students", summary="Get all students enrolled in a teacher's courses")
def get_teacher_students(teacher_id: int, db: Session = Depends(get_db)):
    courses = db.query(Course).filter(Course.teacher_id == teacher_id).all()
    course_ids = [c.id for c in courses]
    
    enrollments = db.query(Enrollment).filter(Enrollment.course_id.in_(course_ids)).all()
    
    results = []
    for enr in enrollments:
        student = enr.student
        course = enr.course
        results.append({
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "course": course.title,
            "progress": 0, # Default for demo
            "lastActive": "Just now",
            "modules": [] # Default for demo
        })
        
    return {"count": len(results), "students": results}

@router.post("/student/{student_id}/enroll/{course_id}", summary="Enroll a student in a course")
def enroll_student(student_id: int, course_id: int, db: Session = Depends(get_db)):
    # Check if student exists, if not, auto-create for the demo
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        student = User(id=student_id, name=f"Demo Student {student_id}", email=f"student_{student_id}@lms.com", role="student")
        db.add(student)
        db.commit()
        db.refresh(student)
        
    # Check if course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Check if already enrolled
    existing = db.query(Enrollment).filter(
        Enrollment.student_id == student_id,
        Enrollment.course_id == course_id
    ).first()
    
    if existing:
        return {"message": "Already enrolled", "enrollment_id": existing.id}
        
    enrollment = Enrollment(student_id=student_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    
    return {"message": "Successfully enrolled", "enrollment_id": enrollment.id}

@router.get("/student/{student_id}/enrollments", summary="Get all active courses for a student")
def get_student_enrollments(student_id: int, db: Session = Depends(get_db)):
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
    
    results = []
    for enr in enrollments:
        course = enr.course
        results.append({
            "enrollment_id": enr.id,
            "enrolled_at": enr.enrolled_at.isoformat(),
            "last_accessed": enr.last_accessed.isoformat(),
            "course": {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "category": course.category,
                "imageUrl": course.image_url,
                "teacher": course.teacher.name if course.teacher else "Unknown",
            }
        })
        
    return {"count": len(results), "enrollments": results}


@router.post(
    "/upload",
    response_model=ProcessedPDFResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and process educational PDF",
    description="Validates, stores, extracts, cleans, detects structure, and chunks an educational PDF document.",
)
async def upload_pdf(file: UploadFile = File(...)):
    # 1. Validate original filename and extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    safe_original_name = os.path.basename(file.filename)
    if not safe_original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files (.pdf) are supported.",
        )

    # 2. Validate Content-Type header if provided
    if file.content_type and file.content_type not in [
        "application/pdf",
        "application/octet-stream",
        "application/x-pdf",
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: '{file.content_type}'. Must be application/pdf.",
        )

    # 3. Read content and validate size & empty status
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes).",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 50MB limit.",
        )

    # 4. Validate PDF magic bytes
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid PDF: missing standard PDF header bytes (%PDF-).",
        )

    # 5. Generate secure unique filename and save to storage
    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}.pdf"
    stored_path = UPLOAD_DIR / stored_filename

    try:
        with open(stored_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded file to storage.",
        ) from exc

    # Persist document metadata mapping for stable document_id resolution
    register_uploaded_document(
        document_id=doc_id,
        original_filename=safe_original_name,
        stored_filename=stored_filename,
    )

    # 6. Execute PDF processing pipeline
    try:
        processed_data = process_pdf(stored_path, original_filename=safe_original_name)
    except PDFExtractionError as exc:
        if stored_path.exists():
            stored_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not process PDF: {str(exc)}",
        ) from exc
    except Exception as exc:
        if stored_path.exists():
            stored_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the PDF document.",
        ) from exc

    # 7. Check if PDF contains extractable text
    meta = processed_data["metadata"]
    if meta["characters"] == 0 or meta["words"] == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
            if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT")
            else 422,
            detail="The provided PDF contains no extractable text. Please upload a PDF with digital text.",
        )

    # 8. Build preview of first few chunks
    chunks_list = processed_data.get("chunks", [])
    preview = [
        ChunkPreview(
            chunk_id=c["chunk_id"],
            page_start=c["page_start"],
            page_end=c["page_end"],
            section=c["section"],
            word_count=c["word_count"],
            character_count=c["character_count"],
        )
        for c in chunks_list[:5]
    ]

    return ProcessedPDFResponse(
        success=True,
        document_id=doc_id,
        filename=safe_original_name,
        stored_filename=stored_filename,
        pages=meta["pages"],
        characters=meta["characters"],
        words=meta["words"],
        chunks=meta["chunks"],
        sections_detected=meta["sections_detected"],
        processing_time=meta["processing_time"],
        chunks_preview=preview,
    )
