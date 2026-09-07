from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Lesson

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.get("/", summary="List all lessons")
def list_lessons(module_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Lesson)
    if module_id is not None:
        query = query.filter(Lesson.module_id == module_id)
    lessons = query.all()
    return {
        "count": len(lessons),
        "lessons": [
            {
                "id": l.id,
                "module_id": l.module_id,
                "title": l.title,
                "summary": l.summary,
                "learning_objective": l.learning_objective,
                "order_number": l.order_number,
            }
            for l in lessons
        ],
    }
