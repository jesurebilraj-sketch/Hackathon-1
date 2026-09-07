from fastapi import APIRouter

router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])


@router.get("/", summary="AI Tutor endpoint stub")
def tutor_status():
    return {"message": "AI Tutor endpoints will be implemented in subsequent phases."}
