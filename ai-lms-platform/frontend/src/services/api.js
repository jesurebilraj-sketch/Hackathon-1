const API_BASE_URL = 'http://localhost:8000/api';

// Helper to handle standard API responses
const handleResponse = async (response) => {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'API request failed');
  }
  return response.json();
};

export const api = {
  // Courses API
  getAllCourses: async (category = null) => {
    const url = category ? `${API_BASE_URL}/courses/?category=${encodeURIComponent(category)}` : `${API_BASE_URL}/courses/`;
    const response = await fetch(url);
    return handleResponse(response);
  },
  
  getCourseDetails: async (courseId) => {
    const response = await fetch(`${API_BASE_URL}/courses/${courseId}`);
    return handleResponse(response);
  },

  createCourse: async (courseData) => {
    const response = await fetch(`${API_BASE_URL}/courses/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(courseData),
    });
    return handleResponse(response);
  },

  // Teacher specific
  getTeacherCourses: async (teacherId) => {
    const response = await fetch(`${API_BASE_URL}/courses/teacher/${teacherId}`);
    return handleResponse(response);
  },

  // Student specific
  enrollStudent: async (studentId, courseId, teacherId = null) => {
    let url = `${API_BASE_URL}/courses/student/${studentId}/enroll/${courseId}`;
    if (teacherId) {
      url += `?teacher_id=${teacherId}`;
    }
    const response = await fetch(url, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  getStudentEnrollments: async (studentId) => {
    const response = await fetch(`${API_BASE_URL}/courses/student/${studentId}/enrollments`);
    return handleResponse(response);
  },
};

