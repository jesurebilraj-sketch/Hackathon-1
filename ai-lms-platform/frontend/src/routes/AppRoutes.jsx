import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import Login from '../pages/auth/Login';
import Register from '../pages/auth/Register';

// Teacher Pages
import TeacherDashboard from '../pages/teacher/TeacherDashboard';
import CreateCourse from '../pages/teacher/CreateCourse';
import CourseBuilder from '../pages/teacher/CourseBuilder';
import TeacherStudents from '../pages/teacher/TeacherStudents';

// Student Pages
import StudentDashboard from '../pages/student/StudentDashboard';
import StudentCourses from '../pages/student/StudentCourses';
import CategoryCourses from '../pages/student/CategoryCourses';

// Common
import Placeholder from '../components/common/Placeholder';

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Protected Teacher Routes */}
        <Route path="/teacher" element={<DashboardLayout role="teacher" />}>
          <Route path="dashboard" element={<TeacherDashboard />} />
          <Route path="courses" element={<Placeholder title="My Courses" />} />
          <Route path="create-course" element={<CreateCourse />} />
          <Route path="courses/:id/builder" element={<CourseBuilder />} />
          <Route path="analytics" element={<Placeholder title="Course Analytics" />} />
          <Route path="students" element={<TeacherStudents />} />
          <Route path="settings" element={<Placeholder title="Teacher Settings" />} />
        </Route>

        {/* Protected Student Routes */}
        <Route path="/student" element={<DashboardLayout role="student" />}>
          <Route path="dashboard" element={<StudentDashboard />} />
          <Route path="courses" element={<StudentCourses />} />
          <Route path="courses/category/:category" element={<CategoryCourses />} />
          <Route path="study-plan" element={<Placeholder title="AI Study Planner" />} />
          <Route path="tutor" element={<Placeholder title="AI Tutor Chat" />} />
          <Route path="progress" element={<Placeholder title="Learning Progress" />} />
          <Route path="settings" element={<Placeholder title="Student Settings" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default AppRoutes;
