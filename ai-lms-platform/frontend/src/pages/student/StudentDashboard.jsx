import React, { useState } from 'react';
import { Target, BookOpen, Clock, Compass } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const StudentDashboard = () => {
  // Demo toggle to switch between new user and active user states
  const [isNewUser, setIsNewUser] = useState(true);
  const navigate = useNavigate();
  const userName = localStorage.getItem('userName') || 'Alex';

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Demo Toggle - Just for hackathon presentation purposes */}
      <div className="flex justify-end mb-4">
        <label className="flex items-center gap-2 cursor-pointer bg-white px-3 py-1.5 rounded-full border border-gray-200 shadow-sm">
          <span className="text-xs font-medium text-gray-500">Demo Mode:</span>
          <div className="relative">
            <input 
              type="checkbox" 
              className="sr-only" 
              checked={!isNewUser}
              onChange={() => setIsNewUser(!isNewUser)} 
            />
            <div className={`block w-10 h-6 rounded-full transition-colors ${!isNewUser ? 'bg-blue-500' : 'bg-gray-300'}`}></div>
            <div className={`absolute left-1 top-1 bg-white w-4 h-4 rounded-full transition-transform ${!isNewUser ? 'transform translate-x-4' : ''}`}></div>
          </div>
          <span className="text-xs font-medium text-gray-700">{isNewUser ? 'New User' : 'Active User'}</span>
        </label>
      </div>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Good Morning, {userName} 👋</h1>
        <p className="text-gray-600 mt-1">
          {isNewUser ? 'Welcome to AI-LMS! Start your learning journey today.' : 'Here is your learning summary for today.'}
        </p>
      </div>

      {isNewUser ? (
        // Empty State for New User
        <div className="glass-card p-12 rounded-2xl border border-white/50 shadow-xl flex flex-col items-center justify-center text-center animate-fade-in-up">
          <div className="w-20 h-20 bg-gradient-to-tr from-blue-100 to-indigo-50 text-blue-600 rounded-full flex items-center justify-center mb-6 shadow-inner">
            <Compass size={40} />
          </div>
          <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-gray-600 mb-3">
            You haven't enrolled in any courses yet
          </h2>
          <p className="text-gray-500 max-w-md mb-8 text-lg">
            Explore our AI-generated courses tailored to your learning pace, or upload a syllabus to let the AI create a custom learning path just for you.
          </p>
          <button 
            onClick={() => navigate('/student/courses')}
            className="px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-bold hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 flex items-center gap-2 transition-all duration-300 transform hover:-translate-y-1"
          >
            <BookOpen size={20} />
            Browse & Register for Courses
          </button>
        </div>
      ) : (
        // Active User State
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in-up">
            <div className="lg:col-span-2 glass-card p-8 rounded-2xl border border-white/50 shadow-xl hover:shadow-2xl transition-shadow duration-300">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Current Course</h2>
                  <p className="text-gray-500">Python Programming</p>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold text-blue-600">78%</span>
                  <p className="text-sm text-gray-500">Overall Progress</p>
                </div>
              </div>
              
              <div className="w-full bg-gray-100 rounded-full h-2.5 mb-6">
                <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: '78%' }}></div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg flex items-center justify-between border border-blue-100">
                <div>
                  <p className="text-sm font-medium text-blue-800 mb-1">Up Next</p>
                  <h3 className="font-bold text-blue-900">Variables and Data Types</h3>
                  <p className="text-sm text-blue-700">Module 1 • Lesson 2</p>
                </div>
                <button className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm">
                  Continue
                </button>
              </div>
            </div>

            <div className="space-y-6">
              <div className="glass-card p-6 rounded-2xl border border-white/50 shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-300 flex items-start gap-4">
                <div className="w-14 h-14 bg-gradient-to-tr from-indigo-100 to-purple-50 text-indigo-600 rounded-2xl flex items-center justify-center shrink-0 shadow-inner">
                  <Target size={28} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Overall Mastery</h3>
                  <p className="text-3xl font-extrabold text-gray-900 mt-1">72%</p>
                </div>
              </div>
              
              <div className="glass-card p-6 rounded-2xl border border-white/50 shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-300 flex items-start gap-4 animate-delay-100">
                <div className="w-14 h-14 bg-gradient-to-tr from-amber-100 to-orange-50 text-amber-600 rounded-2xl flex items-center justify-center shrink-0 shadow-inner">
                  <Clock size={28} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Study Time Today</h3>
                  <p className="text-3xl font-extrabold text-gray-900 mt-1">45m</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-fade-in-up animate-delay-200">
            <div className="glass-card p-8 rounded-2xl border border-white/50 shadow-xl hover:shadow-2xl transition-shadow duration-300">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Today's Study Plan</h2>
              <div className="space-y-4">
                <div className="flex gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors border border-transparent hover:border-gray-100">
                  <div className="flex flex-col items-center justify-center w-16 shrink-0 text-sm">
                    <span className="font-bold text-gray-900">09:00</span>
                    <span className="text-gray-500 text-xs">AM</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900">Variables</h4>
                    <p className="text-sm text-gray-500">Read & Summary</p>
                  </div>
                  <div className="flex items-center text-emerald-600">
                    <span className="text-sm font-medium">Done</span>
                  </div>
                </div>

                <div className="flex gap-4 p-3 rounded-lg border border-blue-100 bg-blue-50">
                  <div className="flex flex-col items-center justify-center w-16 shrink-0 text-sm">
                    <span className="font-bold text-blue-900">10:00</span>
                    <span className="text-blue-700 text-xs">AM</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-blue-900">Practice Quiz</h4>
                    <p className="text-sm text-blue-700">Assessment</p>
                  </div>
                  <div className="flex items-center">
                    <button className="text-sm font-medium text-blue-600 hover:text-blue-800">Start</button>
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card p-8 rounded-2xl border border-white/50 shadow-xl hover:shadow-2xl transition-shadow duration-300">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-900">Needs Attention</h2>
                <span className="text-xs font-medium px-2 py-1 bg-amber-100 text-amber-800 rounded-full">AI Insight</span>
              </div>
              <p className="text-sm text-gray-600 mb-6">
                Based on your recent quizzes, review these topics before moving on.
              </p>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 border border-amber-200 bg-amber-50 rounded-lg">
                  <span className="font-medium text-amber-900">Operators</span>
                  <button className="text-sm font-semibold text-amber-700 hover:text-amber-900">Review Topic</button>
                </div>
                <div className="flex items-center justify-between p-3 border border-amber-200 bg-amber-50 rounded-lg">
                  <span className="font-medium text-amber-900">Loops</span>
                  <button className="text-sm font-semibold text-amber-700 hover:text-amber-900">Review Topic</button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default StudentDashboard;
