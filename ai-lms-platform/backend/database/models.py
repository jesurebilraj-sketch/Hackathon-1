from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean, Float, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), default="student", nullable=False)  # "teacher", "student", "admin"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    courses = relationship("Course", back_populates="teacher", cascade="all, delete-orphan")
    quiz_submissions = relationship("QuizSubmission", back_populates="user", cascade="all, delete-orphan")
    mastery = relationship("UserMastery", back_populates="user", cascade="all, delete-orphan")
    study_preferences = relationship("StudyPreference", back_populates="user", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_file = Column(String(512), nullable=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    teacher = relationship("User", back_populates="courses")
    modules = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order_number",
    )
    quizzes = relationship(
        "Quiz",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    mastery_records = relationship(
        "UserMastery",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    study_preferences = relationship(
        "StudyPreference",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    study_plans = relationship(
        "StudyPlan",
        back_populates="course",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Course id={self.id} title='{self.title}'>"


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_number = Column(Integer, default=1, nullable=False)

    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.order_number",
    )
    quizzes = relationship(
        "Quiz",
        back_populates="module",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Module id={self.id} title='{self.title}' order={self.order_number}>"


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    learning_objective = Column(Text, nullable=True)
    order_number = Column(Integer, default=1, nullable=False)
    estimated_minutes = Column(Integer, default=20, nullable=True)
    difficulty = Column(String(50), default="beginner", nullable=True)
    source_pages = Column(JSON, nullable=True)

    # Phase 4: Rich educational content fields
    learning_objectives = Column(JSON, nullable=True)
    key_concepts = Column(JSON, nullable=True)
    examples = Column(JSON, nullable=True)
    key_takeaways = Column(JSON, nullable=True)
    misconceptions = Column(JSON, nullable=True)
    practice_questions = Column(JSON, nullable=True)

    # Relationships
    module = relationship("Module", back_populates="lessons")
    quizzes = relationship(
        "Quiz",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    mastery = relationship(
        "UserMastery",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    study_sessions = relationship(
        "StudySession",
        back_populates="lesson",
    )

    def __repr__(self):
        return f"<Lesson id={self.id} title='{self.title}' order={self.order_number}>"


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    quiz_type = Column(String(50), default="lesson_quiz", nullable=False)  # "lesson_quiz", "module_quiz", "course_exam"
    passing_score_percentage = Column(Integer, default=70, nullable=False)
    time_limit_minutes = Column(Integer, nullable=True)
    is_fallback = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    course = relationship("Course", back_populates="quizzes")
    module = relationship("Module", back_populates="quizzes")
    lesson = relationship("Lesson", back_populates="quizzes")
    questions = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.order_number",
    )
    submissions = relationship(
        "QuizSubmission",
        back_populates="quiz",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Quiz id={self.id} title='{self.title}'>"


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="multiple_choice", nullable=False)  # "multiple_choice", "true_false", "short_answer"
    options = Column(JSON, nullable=False)  # list of strings e.g. ["Option A", "Option B", "Option C", "Option D"]
    correct_answer = Column(String(512), nullable=False)
    explanation = Column(Text, nullable=False)
    points = Column(Integer, default=1, nullable=False)
    difficulty = Column(String(50), default="medium", nullable=False)  # "easy", "medium", "hard"
    concept = Column(String(255), nullable=True)
    order_number = Column(Integer, default=1, nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")

    def __repr__(self):
        return f"<QuizQuestion id={self.id} quiz_id={self.quiz_id} order={self.order_number}>"


class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    percentage = Column(Float, nullable=False)
    passed = Column(Boolean, default=False, nullable=False)
    answers = Column(JSON, nullable=False)  # submitted answers dict {question_id: answer_str}
    feedback = Column(JSON, nullable=True)  # per-question feedback breakdown
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="submissions")
    user = relationship("User", back_populates="quiz_submissions")

    def __repr__(self):
        return f"<QuizSubmission id={self.id} quiz_id={self.quiz_id} user_id={self.user_id} score={self.score}/{self.max_score}>"


class UserMastery(Base):
    __tablename__ = "user_mastery"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    concept = Column(String(255), nullable=True)
    mastery_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0
    attempts_count = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="needs_review", nullable=False)  # "needs_review", "learning", "proficient", "mastered"
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="mastery")
    course = relationship("Course", back_populates="mastery_records")
    lesson = relationship("Lesson", back_populates="mastery")

    def __repr__(self):
        return f"<UserMastery id={self.id} user_id={self.user_id} score={self.mastery_score}% status='{self.status}'>"


class StudyPreference(Base):
    __tablename__ = "study_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_study_preferences_user_course"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    exam_date = Column(Date, nullable=False)
    daily_study_limit_minutes = Column(Integer, nullable=False)
    available_days = Column(JSON, nullable=False)  # list of lowercase weekday strings e.g. ["monday", "tuesday"]
    availability_windows = Column(JSON, nullable=False)  # list of dicts e.g. [{"start": "18:00", "end": "20:00"}]
    preferred_session_minutes = Column(Integer, default=60, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="study_preferences")
    course = relationship("Course", back_populates="study_preferences")

    def __repr__(self):
        return f"<StudyPreference id={self.id} user_id={self.user_id} course_id={self.course_id} exam_date={self.exam_date}>"


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    exam_date = Column(Date, nullable=False)
    total_planned_minutes = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # "active", "completed"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="study_plans")
    course = relationship("Course", back_populates="study_plans")
    sessions = relationship(
        "StudySession",
        back_populates="study_plan",
        cascade="all, delete-orphan",
        order_by="StudySession.session_date, StudySession.start_time",
    )

    def __repr__(self):
        return f"<StudyPlan id={self.id} user_id={self.user_id} course_id={self.course_id} status='{self.status}'>"


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    study_plan_id = Column(Integer, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    session_date = Column(Date, nullable=False)
    start_time = Column(String(10), nullable=False)  # "18:00"
    end_time = Column(String(10), nullable=False)    # "19:00"
    duration_minutes = Column(Integer, nullable=False)
    session_type = Column(String(50), default="lesson", nullable=False)  # "lesson", "revision"
    status = Column(String(50), default="scheduled", nullable=False)     # "scheduled", "completed", "missed"
    priority = Column(String(50), default="medium", nullable=False)      # "high", "medium", "low"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="sessions")
    lesson = relationship("Lesson", back_populates="study_sessions")

    def __repr__(self):
        return f"<StudySession id={self.id} date={self.session_date} {self.start_time}-{self.end_time} type='{self.session_type}' status='{self.status}'>"


