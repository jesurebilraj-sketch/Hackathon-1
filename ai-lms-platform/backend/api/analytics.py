from fastapi import APIRouter

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/", summary="Analytics endpoint stub")
def analytics_status():
    return {"message": "Analytics endpoints will be implemented in subsequent phases."}
