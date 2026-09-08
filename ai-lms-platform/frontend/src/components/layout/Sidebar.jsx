import React from 'react';
import { NavLink } from 'react-router-dom';
import { BookOpen, Calendar, LayoutDashboard, Settings, Users, BookMarked, LineChart, ShieldCheck, CheckSquare, Clock } from 'lucide-react';

const Sidebar = ({ role }) => {
  const adminLinks = [
    { name: 'Dashboard', path: '/admin/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'Faculty Management', path: '/admin/faculty', icon: <Users size={20} /> },
    { name: 'Course Approvals', path: '/admin/courses', icon: <CheckSquare size={20} /> },
    { name: 'Timetable & Schedule', path: '/admin/timetable', icon: <Clock size={20} /> },
    { name: 'Settings', path: '/admin/settings', icon: <Settings size={20} /> },
  ];

  const teacherLinks = [
    { name: 'Dashboard', path: '/teacher/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'My Courses', path: '/teacher/courses', icon: <BookOpen size={20} /> },
    { name: 'My Timetable', path: '/teacher/timetable', icon: <Clock size={20} /> },
    { name: 'Create Course', path: '/teacher/create-course', icon: <BookMarked size={20} /> },
    { name: 'Course Analytics', path: '/teacher/analytics', icon: <LineChart size={20} /> },
    { name: 'Students', path: '/teacher/students', icon: <Users size={20} /> },
    { name: 'Settings', path: '/teacher/settings', icon: <Settings size={20} /> },
  ];

  const studentLinks = [
    { name: 'Dashboard', path: '/student/dashboard', icon: <LayoutDashboard size={20} /> },
    { name: 'My Courses', path: '/student/courses', icon: <BookOpen size={20} /> },
    { name: 'Study Plan', path: '/student/study-plan', icon: <Calendar size={20} /> },
    { name: 'AI Tutor', path: '/student/tutor', icon: <BookMarked size={20} /> },
    { name: 'Progress', path: '/student/progress', icon: <LineChart size={20} /> },
    { name: 'Settings', path: '/student/settings', icon: <Settings size={20} /> },
  ];

  const links = role === 'admin' ? adminLinks : role === 'teacher' ? teacherLinks : studentLinks;

  return (
    <aside className="w-64 bg-white border-r border-gray-200 hidden md:flex flex-col">
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-blue-600 flex items-center gap-2">
          <BookOpen className="text-blue-600" />
          <span className="text-slate-800">AI-LMS</span>
        </h1>
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {links.map((link) => (
          <NavLink
            key={link.name}
            to={link.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            {link.icon}
            {link.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;

