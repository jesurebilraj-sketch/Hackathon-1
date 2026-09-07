import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BookOpen } from 'lucide-react';

const Register = () => {
  const [role, setRole] = useState('student');
  const navigate = useNavigate();

  const handleRegister = (e) => {
    e.preventDefault();
    const name = e.target.name.value;
    localStorage.setItem('userName', name);
    if (role === 'teacher') {
      navigate('/teacher/dashboard');
    } else {
      navigate('/student/dashboard');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-sm border border-gray-100">
        <div className="flex flex-col items-center">
          <div className="h-12 w-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-4">
            <BookOpen size={28} />
          </div>
          <h2 className="mt-2 text-center text-3xl font-extrabold text-gray-900">
            Create an Account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleRegister}>
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <input name="name" type="text" required className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" placeholder="Full Name" />
            </div>
            <div>
              <input name="email" type="email" required className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" placeholder="Email address" />
            </div>
            <div>
              <input name="password" type="password" required className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" placeholder="Password" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Register As:</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="role" value="student" checked={role === 'student'} onChange={(e) => setRole(e.target.value)} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-sm text-gray-700">Student</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="role" value="teacher" checked={role === 'teacher'} onChange={(e) => setRole(e.target.value)} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-sm text-gray-700">Teacher</span>
                </label>
              </div>
            </div>
          </div>
          <div>
            <button type="submit" className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">Sign up</button>
          </div>
          <div className="text-center text-sm">
            <span className="text-gray-600">Already have an account? </span>
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">Sign in</Link>
          </div>
        </form>
      </div>
    </div>
  );
};
export default Register;

