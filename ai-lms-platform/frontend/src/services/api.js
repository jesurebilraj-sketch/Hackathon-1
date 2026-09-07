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
  getAllCourses: async () => {
    const response = await fetch(`${API_BASE_URL}/courses/`);
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
  enrollStudent: async (studentId, courseId) => {
    const response = await fetch(`${API_BASE_URL}/courses/student/${studentId}/enroll/${courseId}`, {
      method: 'POST',
    });
    return handleResponse(response);
  },

  getStudentEnrollments: async (studentId) => {
    const response = await fetch(`${API_BASE_URL}/courses/student/${studentId}/enrollments`);
    return handleResponse(response);
  },
};

