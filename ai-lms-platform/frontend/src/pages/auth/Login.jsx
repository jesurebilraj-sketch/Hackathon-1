import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BookOpen, Eye, EyeOff, AlertCircle } from 'lucide-react';

const Login = () => {
  const [role, setRole] = useState('student');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Valid teacher accounts for the demo
  const validTeacherEmails = [
    'teacher@lms.com',
    'alan.turing@lms.edu',
    'grace.hopper@lms.edu',
    'ada.lovelace@lms.edu'
  ];

  const validatePassword = (password) => {
    // Password security check: 
    // Minimum 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special character
    const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;
    return regex.test(password);
  };

  const handleLogin = (e) => {
    e.preventDefault();
    setError(''); // clear previous errors
    
    const email = e.target.email.value.toLowerCase().trim();
    const password = e.target.password.value;

    // 1. Password Security Check
    if (!validatePassword(password)) {
      setError('Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one number, and one special character (e.g., SecurePass123!).');
      return;
    }

    // 2. Role validation check
    if (role === 'teacher') {
      if (!validTeacherEmails.includes(email)) {
        setError('Invalid Teacher Email. Access denied. Please use a registered teacher account (e.g., alan.turing@lms.edu).');
        return;
      }
    }

    // 3. Success -> Proceed to login
    const namePart = email.split('@')[0];
    const cleanName = namePart.replace(/[.-]/g, ' '); // alan.turing -> alan turing
    const capitalizedName = cleanName.split(' ').map(n => n.charAt(0).toUpperCase() + n.slice(1)).join(' ');
    
    localStorage.setItem('userName', capitalizedName);
    
    if (role === 'teacher') {
      // Set teacher ID for mock dashboard data
      if (email === 'alan.turing@lms.edu') localStorage.setItem('teacherId', '1');
      else if (email === 'grace.hopper@lms.edu') localStorage.setItem('teacherId', '2');
      else if (email === 'ada.lovelace@lms.edu') localStorage.setItem('teacherId', '3');
      else localStorage.setItem('teacherId', '1');

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
            Sign in to AI-LMS
          </h2>
        </div>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start gap-3 text-sm">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleLogin}>
          <div className="space-y-4 rounded-md shadow-sm">
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                {role === 'student' ? 'Student Email:' : 'Teacher Email:'}
              </label>
              <input 
                name="email" 
                type="email" 
                required 
                className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm" 
                placeholder="email@example.com" 
                defaultValue="alan.turing@lms.edu" 
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-500 mb-1">
                Password:
              </label>
              <div className="relative">
                <input 
                  name="password" 
                  type={showPassword ? "text" : "password"} 
                  required 
                  className="relative block w-full px-3 py-3 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm pr-10" 
                  placeholder="Password" 
                  defaultValue="SecurePass123!" 
                />
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
              <label className="block text-sm font-medium text-gray-700 mb-2">Login As:</label>
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
            <button type="submit" className="w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 cursor-pointer transition-colors">Sign in</button>
          </div>
          <div className="text-center text-sm">
            <span className="text-gray-600">Don't have an account? </span>
            <Link to="/register" className="font-medium text-blue-600 hover:text-blue-500">Register here</Link>
          </div>
        </form>
      </div>
    </div>
  );
};
export default Login;

