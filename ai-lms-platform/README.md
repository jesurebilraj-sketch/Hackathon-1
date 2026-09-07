# AI-LMS Platform

Welcome to the AI-LMS Platform repository! This is a modern, AI-powered Learning Management System with distinct Teacher and Student portals.

## Demo Credentials

For convenience during demonstrations, the following accounts have been registered and validated for use. All accounts share the same secure default password.

**Default Password for ALL accounts:**
`SecurePass123!`

### Teacher Accounts
*Note: Teacher login is strictly validated. You MUST use one of the following emails to access the Teacher Dashboard.*

1. **Dr. Alan Turing** (Theoretical & Intensive)
   - Email: `alan.turing@lms.edu`
2. **Prof. Grace Hopper** (Practical & Project-Based)
   - Email: `grace.hopper@lms.edu`
3. **Dr. Ada Lovelace** (Paced & Beginner Friendly)
   - Email: `ada.lovelace@lms.edu`
4. **General Admin Teacher**
   - Email: `teacher@lms.com`

### Student Accounts
*Note: Student registration is open, so you can use any email to log in as a student, but this is the default pre-filled demo account.*

1. **Demo Student**
   - Email: `student@lms.com`

## Quick Start

### Frontend
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`

### Backend
1. Navigate to the backend directory: `cd backend`
2. Create virtual environment: `python -m venv venv`
3. Activate environment: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install requirements: `pip install -r requirements.txt`
5. Run the server: `uvicorn main:app --reload`
6. *(Optional)* Seed the database with realistic courses: `python seed.py`

