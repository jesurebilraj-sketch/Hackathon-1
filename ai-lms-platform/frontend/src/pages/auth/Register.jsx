import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BookOpen, Eye, EyeOff, AlertCircle } from 'lucide-react';

const Register = () => {
  const [role, setRole] = useState('student');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const validatePassword = (password) => {
    // Password security check: 
    // Minimum 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(password);
  };

  const handleRegister = (e) => {
    e.preventDefault();
    setError('');

    const password = e.target.password.value;
    const email = e.target.email.value.toLowerCase().trim();

    // Password Security Check
    if (!validatePassword(password)) {
      setError('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character.');
      return;
    }

    // Role validation check
    const isLmsEdu = email.endsWith('@lms.edu');
    const isAdminDomain = email.endsWith('@admin.lms.edu') || email === 'admin@lms.edu';
    
    if (role === 'admin') {
      if (!isAdminDomain) {
        setError('Administrator registration requires an @admin.lms.edu or admin@lms.edu email.');
        return;
      }
    } else if (role === 'teacher') {
      if (!isLmsEdu) {
        setError('Teacher emails must end with @lms.edu. Please use a valid institutional email.');
        return;
      }
    } else if (role === 'student') {
      if (isLmsEdu || isAdminDomain) {
        setError('Institutional emails (@lms.edu / @admin.lms.edu) are reserved for Faculty and Administrators. Please select the appropriate portal.');
        return;
      }
    }

    const name = e.target.name.value;
    localStorage.setItem('userName', name);
    localStorage.setItem('userEmail', email);
    localStorage.setItem('userRole', role);

    if (role === 'admin') {
      navigate('/admin/dashboard');
    } else if (role === 'teacher') {
      // Set a generic teacher ID for demo
      localStorage.setItem('teacherId', '1');
      navigate('/teacher/dashboard');
    } else {
      // Generate a stable student ID based on email string
      let hash = 0;
      for (let i = 0; i < email.length; i++) {
          hash = email.charCodeAt(i) + ((hash << 5) - hash);
      }
      const studentId = Math.abs(hash) % 10000;
      localStorage.setItem('studentId', studentId.toString());

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

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3 text-sm">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleRegister}>
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                {role === 'student' ? 'Student Name:' : 'Teacher Name:'}
              </label>
              <input name="name" type="text" required className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" placeholder="Full Name" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                {role === 'student' ? 'Student Email:' : 'Teacher Email:'}
              </label>
              <input name="email" type="email" required className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" placeholder="Email address" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                Password:
              </label>
              <div className="relative">
                <input name="password" type={showPassword ? "text" : "password"} required className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm pr-10" placeholder="Password" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 cursor-pointer"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Register As:</label>
              <div className="grid grid-cols-3 gap-2">
                <label className="flex items-center gap-1.5 cursor-pointer bg-gray-50 p-2.5 rounded-lg border border-gray-200 hover:bg-blue-50 transition-colors">
                  <input type="radio" name="role" value="student" checked={role === 'student'} onChange={(e) => setRole(e.target.value)} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-xs sm:text-sm font-medium text-gray-700">Student</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer bg-gray-50 p-2.5 rounded-lg border border-gray-200 hover:bg-blue-50 transition-colors">
                  <input type="radio" name="role" value="teacher" checked={role === 'teacher'} onChange={(e) => setRole(e.target.value)} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-xs sm:text-sm font-medium text-gray-700">Teacher</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer bg-gray-50 p-2.5 rounded-lg border border-gray-200 hover:bg-blue-50 transition-colors">
                  <input type="radio" name="role" value="admin" checked={role === 'admin'} onChange={(e) => setRole(e.target.value)} className="text-blue-600 focus:ring-blue-500" />
                  <span className="text-xs sm:text-sm font-medium text-gray-700">Administrator</span>
                </label>
              </div>
            </div>
          </div>
          <div>
            <button type="submit" className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 cursor-pointer transition-colors">Create Account</button>
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

