import React from 'react';
import { Upload, BookOpen, Users } from 'lucide-react';

const TeacherDashboard = () => {
  const userName = localStorage.getItem('userName') || 'Professor';
  const teacherId = localStorage.getItem('teacherId') || '1';
  
  const savedStats = localStorage.getItem('teacherStats');
  const teacherStats = savedStats ? JSON.parse(savedStats) : { 1: 0, 2: 0, 3: 0 };
  const totalStudents = teacherStats[teacherId] || 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Welcome back, {userName}</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col items-center justify-center text-center space-y-4 hover:border-blue-300 hover:shadow-md cursor-pointer transition-all">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center">
            <Upload size={32} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Upload Material</h3>
            <p className="text-sm text-gray-500 mt-1">Generate a new AI course from a PDF</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-start gap-4">
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center shrink-0">
            <BookOpen size={24} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Active Courses</h3>
            <p className="text-3xl font-bold mt-2">4</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-start gap-4">
          <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center shrink-0">
            <Users size={24} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Total Students</h3>
            <p className="text-3xl font-bold mt-2">{totalStudents}</p>
          </div>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Courses</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="group bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between overflow-hidden">
            <div className="h-32 w-full overflow-hidden bg-gray-100">
              <img src="https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80" alt="Python Programming" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            </div>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900">Python Programming</h3>
              <p className="text-sm text-gray-500 mt-1">8 Modules • 32 Lessons</p>
              <div className="mt-6 flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">75 Students</span>
                <button className="px-4 py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium hover:bg-blue-100">
                  View Course
                </button>
              </div>
            </div>
          </div>
          
          <div className="group bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between overflow-hidden">
            <div className="h-32 w-full overflow-hidden bg-gray-100">
              <img src="https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80" alt="Data Structures" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
            </div>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900">Data Structures</h3>
              <p className="text-sm text-gray-500 mt-1">6 Modules • 24 Lessons</p>
              <div className="mt-6 flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">42 Students</span>
                <button className="px-4 py-2 bg-blue-50 text-blue-600 rounded-md text-sm font-medium hover:bg-blue-100">
                  View Course
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default TeacherDashboard;

