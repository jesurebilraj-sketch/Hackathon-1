from fastapi import APIRouter

router = APIRouter(prefix="/api/quizzes", tags=["Quizzes"])


@router.get("/", summary="Quiz endpoint stub")
def list_quizzes():
    return {"message": "Quiz endpoints will be implemented in subsequent phases."}
