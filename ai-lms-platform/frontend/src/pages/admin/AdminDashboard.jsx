import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, BookOpen, CheckSquare, Clock, ArrowUpRight, Plus, ShieldCheck, AlertCircle, Calendar } from 'lucide-react';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [facultyCount, setFacultyCount] = useState(3);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [activeCoursesCount, setActiveCoursesCount] = useState(4);
  const [timetableCount, setTimetableCount] = useState(0);

  useEffect(() => {
    // 1. Calculate Faculty
    const customFaculty = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    setFacultyCount(3 + customFaculty.length); // 3 default teachers + custom

    // 2. Pending Course Requests from Teachers
    const requests = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    setPendingRequests(requests.filter(r => r.status === 'pending'));

    // 3. Approved / Available Courses
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    setActiveCoursesCount(4 + approved.length); // 4 default trending + approved

    // 4. Timetable Entries
    const timetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
    setTimetableCount(timetables.length);
  }, []);

  const stats = [
    { title: 'Total Faculty', value: facultyCount, icon: <Users size={22} />, color: 'bg-blue-500', link: '/admin/faculty' },
    { title: 'Active Courses', value: activeCoursesCount, icon: <BookOpen size={22} />, color: 'bg-emerald-500', link: '/admin/courses' },
    { title: 'Pending Approvals', value: pendingRequests.length, icon: <CheckSquare size={22} />, color: 'bg-amber-500', link: '/admin/courses' },
    { title: 'Scheduled Timetables', value: timetableCount, icon: <Clock size={22} />, color: 'bg-indigo-500', link: '/admin/timetable' },
  ];

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 flex items-center gap-1">
              <ShieldCheck size={12} /> University Administrator Portal
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Administrator Console</h1>
          <p className="text-gray-600 mt-1">Manage institutional faculty, review course requests, and supervise schedules.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/admin/faculty')}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm cursor-pointer"
          >
            <Plus size={16} /> Add Faculty
          </button>
          <button 
            onClick={() => navigate('/admin/courses')}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer"
          >
            <CheckSquare size={16} /> Course Approvals ({pendingRequests.length})
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat, idx) => (
          <div 
            key={idx}
            onClick={() => navigate(stat.link)}
            className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-500">{stat.title}</span>
              <div className={`w-10 h-10 rounded-lg ${stat.color} text-white flex items-center justify-center`}>
                {stat.icon}
              </div>
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-3xl font-bold text-gray-900">{stat.value}</span>
              <span className="text-xs font-semibold text-blue-600 flex items-center gap-0.5 hover:underline">
                Manage <ArrowUpRight size={14} />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: Pending Course Requests & System Schedule Guidelines */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Pending Requests Column */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-100">
            <div>
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <CheckSquare className="text-blue-600" size={20} />
                Course Requests from Teachers
              </h2>
              <p className="text-sm text-gray-500">Teachers have submitted these courses for curriculum approval.</p>
            </div>
            <button 
              onClick={() => navigate('/admin/courses')}
              className="text-xs font-medium text-blue-600 hover:text-blue-800"
            >
              View All
            </button>
          </div>

          {pendingRequests.length === 0 ? (
            <div className="text-center py-10">
              <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <ShieldCheck size={28} />
              </div>
              <h3 className="text-sm font-semibold text-gray-900">All caught up!</h3>
              <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                There are no pending course requests awaiting administrative review. New requests from faculty will show up here.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingRequests.slice(0, 3).map((req) => (
                <div key={req.id} className="p-4 rounded-lg border border-gray-200 bg-gray-50/50 hover:bg-gray-50 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-semibold px-2 py-0.5 bg-amber-100 text-amber-800 rounded-md uppercase">
                      Pending Review
                    </span>
                    <h3 className="text-base font-bold text-gray-900 mt-1">{req.title}</h3>
                    <p className="text-xs text-gray-500">Requested by: <span className="font-medium text-gray-700">{req.teacherName || 'Faculty Member'}</span> • {req.category || 'General'}</p>
                  </div>
                  <button
                    onClick={() => navigate('/admin/courses')}
                    className="px-3.5 py-2 bg-blue-600 text-white rounded-lg text-xs font-medium hover:bg-blue-700 shrink-0 shadow-sm cursor-pointer"
                  >
                    Review & Approve
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Institutional Policies & Constraints Card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-5">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <AlertCircle className="text-indigo-600" size={20} />
            University Policies & Scheduling Rules
          </h2>
          <div className="space-y-4 text-xs leading-relaxed text-gray-600">
            <div className="p-3 bg-blue-50/70 border border-blue-100 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-1 flex items-center gap-1.5">
                <Clock size={14} className="text-blue-600" /> Regular Course Lecture Limit
              </h4>
              <p className="text-blue-800">
                All regular class timetables <strong>must end before 6:00 PM</strong> (08:00 AM – 06:00 PM). Night-time regular lectures are strictly prohibited by academic policy.
              </p>
            </div>

            <div className="p-3 bg-amber-50/70 border border-amber-100 rounded-lg">
              <h4 className="font-semibold text-amber-900 mb-1 flex items-center gap-1.5">
                <Calendar size={14} className="text-amber-600" /> Practice & Lab Sessions
              </h4>
              <p className="text-amber-800">
                Hands-on practice, coding labs, and study groups <strong>must be scheduled after 6:30 PM</strong> (18:30 – 22:00) to allow students dedicated preparation time.
              </p>
            </div>

            <div className="p-3 bg-purple-50/70 border border-purple-100 rounded-lg">
              <h4 className="font-semibold text-purple-900 mb-1 flex items-center gap-1.5">
                <ShieldCheck size={14} className="text-purple-600" /> 5-Course Student Limit
              </h4>
              <p className="text-purple-800">
                To prevent academic burnout, students are strictly capped at taking a maximum of <strong>5 courses</strong> concurrently.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default AdminDashboard;
