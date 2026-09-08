import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, BookOpen, Users, Clock, Calendar, ArrowRight, Sun, Moon, Sliders } from 'lucide-react';

const TeacherDashboard = () => {
  const navigate = useNavigate();
  const userName = localStorage.getItem('userName') || 'Professor';
  const userEmail = localStorage.getItem('userEmail') || '';
  const teacherId = localStorage.getItem('teacherId') || '1';
  
  const savedStats = localStorage.getItem('teacherStats');
  const teacherStats = savedStats ? JSON.parse(savedStats) : { 1: 0, 2: 0, 3: 0 };
  const totalStudents = teacherStats[teacherId] || 0;

  const [mySlots, setMySlots] = useState([]);
  const [activeCoursesCount, setActiveCoursesCount] = useState(0);
  const [actualStudentCount, setActualStudentCount] = useState(0);

  useEffect(() => {
    // 1. Real Active Courses Handled by this teacher
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    const lastName = userName.split(' ').pop();
    const myCourses = approved.filter(c => {
      if (c.teacherEmail && c.teacherEmail.toLowerCase() === userEmail.toLowerCase()) return true;
      if (c.instructor && (c.instructor === userName || c.instructor.includes(lastName))) return true;
      if (c.teacher && (c.teacher === userName || c.teacher.includes(lastName))) return true;
      return false;
    });
    setActiveCoursesCount(myCourses.length);

    // 2. Timetable - strictly only for approved courses
    const allTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
    const filtered = allTimetables.filter(slot => {
      // Must be an approved course
      const isApproved = approved.some(ac => ac.id === slot.courseId || ac.title?.toLowerCase() === slot.courseTitle?.toLowerCase());
      if (!isApproved) return false;

      if (slot.instructor === userName) return true;
      if (slot.teacherId && slot.teacherId.toString() === teacherId.toString()) return true;
      return slot.instructor && slot.instructor.includes(lastName);
    });
    setMySlots(filtered);

    // 3. Real Student Count enrolled in this teacher's courses
    let uniqueStudents = new Set();
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('mockEnrollments_')) {
        const studentEmail = key.replace('mockEnrollments_', '');
        try {
          const enrs = JSON.parse(localStorage.getItem(key) || '[]');
          for (const enr of enrs) {
            const courseObj = enr.course || enr;
            if (myCourses.some(mc => mc.id === courseObj.id || mc.title === courseObj.title)) {
              uniqueStudents.add(studentEmail);
            }
          }
        } catch (e) {}
      }
    }
    setActualStudentCount(uniqueStudents.size);
  }, [userName, userEmail, teacherId]);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back, {userName}</h1>
          <p className="text-gray-500 text-sm mt-0.5">Faculty Dashboard • Manage courses, students, and your personal teaching timetable.</p>
        </div>
        <button
          onClick={() => navigate('/teacher/timetable')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Sliders size={16} /> Adjust My Timetable
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div 
          onClick={() => navigate('/teacher/create-course')}
          className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col items-center justify-center text-center space-y-4 hover:border-blue-300 hover:shadow-md cursor-pointer transition-all"
        >
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
            <p className="text-3xl font-bold mt-2">{activeCoursesCount}</p>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-start gap-4">
          <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center shrink-0">
            <Users size={24} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Total Students</h3>
            <p className="text-3xl font-bold mt-2">{actualStudentCount}</p>
          </div>
        </div>
      </div>

      {/* My Teaching Schedule Widget */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Clock className="text-blue-600" size={18} />
              My Teaching Timetable & Schedule Preferences
            </h3>
            <p className="text-xs text-gray-500">You have full autonomy to adjust your teaching hours and practice sessions.</p>
          </div>
          <button
            onClick={() => navigate('/teacher/timetable')}
            className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
          >
            Adjust Timetable <ArrowRight size={14} />
          </button>
        </div>

        {mySlots.length === 0 ? (
          <div className="text-center py-6 text-xs text-gray-500">
            You haven't customized your teaching timetable yet.
            <button
              onClick={() => navigate('/teacher/timetable')}
              className="ml-2 font-bold text-blue-600 hover:underline"
            >
              Set your preferred schedule now &rarr;
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {mySlots.slice(0, 3).map((slot) => (
              <div 
                key={slot.id} 
                className={`p-3.5 rounded-lg border text-xs flex flex-col justify-between ${
                  slot.sessionType === 'class'
                    ? 'bg-blue-50/50 border-blue-200'
                    : 'bg-purple-50/50 border-purple-200'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`px-2 py-0.5 rounded font-bold uppercase text-[9px] ${
                      slot.sessionType === 'class' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                    }`}>
                      {slot.sessionType === 'class' ? 'Lecture (< 6 PM)' : 'Practice Lab (> 6:30 PM)'}
                    </span>
                    <span className="font-semibold text-gray-700">{slot.day}</span>
                  </div>
                  <h4 className="font-bold text-gray-900 text-sm mt-1 mb-0.5">{slot.courseTitle}</h4>
                </div>
                <div className="pt-2 border-t border-gray-200/50 flex items-center justify-between font-semibold text-gray-700 mt-2">
                  <span>{slot.startTime} – {slot.endTime}</span>
                  <span className="text-gray-500 font-normal">{slot.room}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
export default TeacherDashboard;

