from fastapi import APIRouter

router = APIRouter(prefix="/api/planner", tags=["Study Planner"])


@router.get("/", summary="Study Planner endpoint stub")
def planner_status():
    return {"message": "Study Planner endpoints will be implemented in subsequent phases."}
