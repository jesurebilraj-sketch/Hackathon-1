import os
import random
from sqlalchemy.orm import Session
from database.database import SessionLocal, init_db
from database.models import User, Course, Module, Lesson

def seed():
    init_db()
    db = SessionLocal()
    
    # 1. Create a teacher
    teacher = db.query(User).filter(User.email == "teacher@lms.com").first()
    if not teacher:
        teacher = User(name="Expert Instructor", email="teacher@lms.com", role="teacher")
        db.add(teacher)
        db.commit()
        db.refresh(teacher)

    # 2. Define realistic courses with category and unique images
    seed_data = [
        {"title": "Full-Stack React & Node.js", "category": "Web Development", "img": "https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=500&q=80"},
        {"title": "CSS Tailwind Mastery", "category": "Web Development", "img": "https://images.unsplash.com/photo-1507721999472-8ed4421c4af2?w=500&q=80"},
        {"title": "Advanced Differential Equations", "category": "Mathematics", "img": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=500&q=80"},
        {"title": "Linear Algebra for ML", "category": "Mathematics", "img": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=500&q=80"},
        {"title": "The Roman Empire", "category": "History", "img": "https://images.unsplash.com/photo-1552314711-66236b281b37?w=500&q=80"},
        {"title": "Cold War Politics", "category": "History", "img": "https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=500&q=80"},
        {"title": "Quantum Mechanics", "category": "Physics", "img": "https://images.unsplash.com/photo-1636466497217-26a8cbeaf0aa?w=500&q=80"},
        {"title": "Astrophysics 101", "category": "Physics", "img": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=500&q=80"},
        {"title": "Algorithms and Data Structures", "category": "Computer Science", "img": "https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80"},
        {"title": "Operating Systems Design", "category": "Computer Science", "img": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=500&q=80"},
        {"title": "Cellular Biology", "category": "Biology", "img": "https://images.unsplash.com/photo-1530026405186-ed1f139313f8?w=500&q=80"},
        {"title": "Genetics & DNA", "category": "Biology", "img": "https://images.unsplash.com/photo-1576086271223-f36b6d859ce8?w=500&q=80"},
        {"title": "Organic Chemistry", "category": "Chemistry", "img": "https://images.unsplash.com/photo-1603126859596-f6d89fc284e9?w=500&q=80"},
        {"title": "Inorganic Chemistry", "category": "Chemistry", "img": "https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=500&q=80"},
        {"title": "Python for Data Science", "category": "Data Science", "img": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=500&q=80"},
        {"title": "Data Visualization with Tableau", "category": "Data Science", "img": "https://images.unsplash.com/photo-1543286386-2e659306cd6c?w=500&q=80"},
        {"title": "Deep Learning with PyTorch", "category": "Machine Learning", "img": "https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=500&q=80"},
        {"title": "Reinforcement Learning", "category": "Machine Learning", "img": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=500&q=80"},
        {"title": "Renaissance Art", "category": "Art History", "img": "https://images.unsplash.com/photo-1578301978018-3005759f48f7?w=500&q=80"},
        {"title": "Modern Art Movements", "category": "Art History", "img": "https://images.unsplash.com/photo-1543857778-c4a1a3e0b2eb?w=500&q=80"},
    ]

    # Delete existing courses
    db.query(Course).delete()
    
    for item in seed_data:
        course = Course(
            title=item["title"],
            description=f"Learn everything about {item['title']} in this comprehensive course.",
            teacher_id=teacher.id,
            category=item["category"],
            image_url=item["img"]
        )
        db.add(course)
    
    db.commit()
    print("Database seeded with realistic courses!")

if __name__ == "__main__":
    seed()

