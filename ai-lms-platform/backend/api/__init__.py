from .courses import router as courses_router
from .course_generation import router as course_generation_router
from .lessons import router as lessons_router
from .quizzes import router as quizzes_router
from .mastery import router as mastery_router
from .tutor import router as tutor_router
from .planner import router as planner_router
from .analytics import router as analytics_router

__all__ = [
    "courses_router",
    "course_generation_router",
    "lessons_router",
    "quizzes_router",
    "mastery_router",
    "tutor_router",
    "planner_router",
    "analytics_router",
]
