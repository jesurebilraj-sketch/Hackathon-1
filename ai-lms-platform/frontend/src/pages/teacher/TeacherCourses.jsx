import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Users, Plus, Clock, CheckCircle, ArrowUpRight, BookMarked, Settings, Layers } from 'lucide-react';

const TeacherCourses = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('approved'); // 'approved' | 'pending'
  const [approvedCourses, setApprovedCourses] = useState([]);
  const [pendingCourses, setPendingCourses] = useState([]);
  const [studentCounts, setStudentCounts] = useState({});
  const [courseTimetables, setCourseTimetables] = useState([]);

  const userName = localStorage.getItem('userName') || 'Teacher';
  const userEmail = localStorage.getItem('userEmail') || 'teacher@lms.edu';
  const teacherId = localStorage.getItem('teacherId') || '1';

  // Base catalog of known courses
  const defaultCourses = [
    {
      id: 101,
      title: 'Advanced React Patterns',
      category: 'Web Development',
      instructor: 'Dr. Alan Turing',
      teacherEmail: 'alan.turing@lms.edu',
      description: 'Master higher-order components, custom hooks, and state machines in React.',
      imageUrl: 'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=500&q=80',
      modules: 8,
      lessons: 32,
      status: 'Live & Approved'
    },
    {
      id: 102,
      title: 'Calculus I',
      category: 'Mathematics',
      instructor: 'Dr. Ada Lovelace',
      teacherEmail: 'ada.lovelace@lms.edu',
      description: 'Differential and integral calculus with rigorous applications in physics and computation.',
      imageUrl: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=500&q=80',
      modules: 10,
      lessons: 40,
      status: 'Live & Approved'
    },
    {
      id: 103,
      title: 'Software Engineering & Clean Architecture',
      category: 'Software Engineering',
      instructor: 'Prof. Grace Hopper',
      teacherEmail: 'grace.hopper@lms.edu',
      description: 'Enterprise design patterns, CI/CD pipelines, and robust modular architectures.',
      imageUrl: 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=500&q=80',
      modules: 7,
      lessons: 28,
      status: 'Live & Approved'
    },
    {
      id: 104,
      title: 'Python Programming',
      category: 'Computer Science',
      instructor: 'Dr. Alan Turing',
      teacherEmail: 'alan.turing@lms.edu',
      description: 'Comprehensive Python mastery from basic scripting to asynchronous microservices.',
      imageUrl: 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80',
      modules: 9,
      lessons: 36,
      status: 'Live & Approved'
    },
    {
      id: 105,
      title: 'Data Structures & Algorithms',
      category: 'Computer Science',
      instructor: 'Prof. Grace Hopper',
      teacherEmail: 'grace.hopper@lms.edu',
      description: 'Deep dive into binary trees, graph algorithms, dynamic programming, and complexity.',
      imageUrl: 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80',
      modules: 6,
      lessons: 24,
      status: 'Live & Approved'
    }
  ];

  useEffect(() => {
    // 1. Load approved courses from localStorage
    const storedApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    // 2. Load pending courses from this teacher
    const storedPending = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');

    const allApprovedCatalog = [...defaultCourses, ...storedApproved];

    // Filter approved courses strictly handled by this logged-in teacher
    const lastName = userName.split(' ').pop();
    const handledApproved = allApprovedCatalog.filter(c => {
      if (c.teacherEmail && c.teacherEmail.toLowerCase() === userEmail.toLowerCase()) return true;
      if (c.instructor && (c.instructor === userName || c.instructor.includes(lastName))) return true;
      if (c.teacher && (c.teacher === userName || c.teacher.includes(lastName))) return true;
      return false;
    });
    setApprovedCourses(handledApproved);

    // Filter pending requests created by this teacher
    const myPending = storedPending.filter(p => 
      (p.teacherEmail && p.teacherEmail.toLowerCase() === userEmail.toLowerCase()) || 
      p.teacherName === userName
    ).map(p => ({
      ...p,
      status: 'Pending Admin Approval',
      modulesCount: Array.isArray(p.modules) ? p.modules.length : (p.modules || 4)
    }));
    setPendingCourses(myPending);

    // 3. Calculate student enrollments per course
    const counts = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('mockEnrollments_')) {
        try {
          const enrs = JSON.parse(localStorage.getItem(key) || '[]');
          for (const enr of enrs) {
            const courseTitle = enr.course?.title;
            if (courseTitle) {
              counts[courseTitle] = (counts[courseTitle] || 0) + 1;
            }
          }
        } catch (e) {}
      }
    }
    setStudentCounts(counts);

    // 4. Load Timetables
    const allTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
    setCourseTimetables(allTimetables);
  }, [userName, userEmail, teacherId]);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 flex items-center gap-1">
              <BookOpen size={12} /> Instructor Curriculum Management
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Courses Handled by {userName}</h1>
          <p className="text-gray-600 text-sm mt-0.5">
            Manage your approved teaching catalog and track courses awaiting administrator review.
          </p>
        </div>

        <button
          onClick={() => navigate('/teacher/create-course')}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Plus size={18} /> Create New Course
        </button>
      </div>

      {/* Two Feature Tabs: 1) Approved Courses, 2) Courses Pending Administrator Approval */}
      <div className="flex items-center border-b border-gray-200 gap-2">
        <button
          onClick={() => setActiveTab('approved')}
          className={`flex items-center gap-2 pb-3 px-4 text-sm font-bold border-b-2 transition-all cursor-pointer ${
            activeTab === 'approved'
              ? 'border-emerald-600 text-emerald-700 bg-emerald-50/50 rounded-t-lg'
              : 'border-transparent text-gray-500 hover:text-gray-800'
          }`}
        >
          <CheckCircle size={16} className={activeTab === 'approved' ? 'text-emerald-600' : 'text-gray-400'} />
          1) Approved Courses
          <span className={`text-xs px-2 py-0.5 rounded-full font-bold ml-1 ${
            activeTab === 'approved' ? 'bg-emerald-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}>
            {approvedCourses.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('pending')}
          className={`flex items-center gap-2 pb-3 px-4 text-sm font-bold border-b-2 transition-all cursor-pointer ${
            activeTab === 'pending'
              ? 'border-amber-600 text-amber-700 bg-amber-50/50 rounded-t-lg'
              : 'border-transparent text-gray-500 hover:text-gray-800'
          }`}
        >
          <Clock size={16} className={activeTab === 'pending' ? 'text-amber-600' : 'text-gray-400'} />
          2) Courses Pending for Administrator's Approval
          <span className={`text-xs px-2 py-0.5 rounded-full font-bold ml-1 ${
            activeTab === 'pending' ? 'bg-amber-600 text-white' : 'bg-gray-100 text-gray-600'
          }`}>
            {pendingCourses.length}
          </span>
        </button>
      </div>

      {/* Content Rendering based on Active Tab */}
      {activeTab === 'approved' ? (
        // FEATURE 1: Approved Courses
        <div>
          {approvedCourses.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-sm">
              <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle size={32} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">No Approved Courses Yet</h3>
              <p className="text-sm text-gray-500 max-w-md mx-auto mb-6">
                Courses approved by the university administrator will appear here with active student enrollments and timetable management.
              </p>
              <button
                onClick={() => navigate('/teacher/create-course')}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors shadow-sm"
              >
                Create Course for Review
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {approvedCourses.map((course) => {
                const enrolled = studentCounts[course.title] || 0;
                const moduleCount = Array.isArray(course.modules) ? course.modules.length : (course.modules || 0);
                const slots = courseTimetables.filter(t => t.courseTitle === course.title);

                return (
                  <div 
                    key={course.id} 
                    className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col justify-between"
                  >
                    <div>
                      <div className="h-44 w-full overflow-hidden relative bg-gray-100">
                        <img 
                          src={course.imageUrl || 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80'} 
                          alt={course.title} 
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                        <span className="absolute top-3 right-3 px-2.5 py-0.5 rounded-full text-[11px] font-bold shadow-sm bg-emerald-600 text-white flex items-center gap-1">
                          <CheckCircle size={12} /> Approved & Live
                        </span>
                      </div>

                      <div className="p-6 space-y-3">
                        <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
                          {course.category}
                        </span>
                        <h3 className="font-bold text-gray-900 text-lg leading-snug">{course.title}</h3>
                        <p className="text-xs text-gray-500 line-clamp-2">{course.description}</p>

                        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-100 text-xs text-gray-600">
                          <div className="flex items-center gap-1.5 font-medium">
                            <Users size={14} className="text-blue-500" />
                            <span>{enrolled} Student{enrolled === 1 ? '' : 's'}</span>
                          </div>
                          <div className="flex items-center gap-1.5 font-medium">
                            <Layers size={14} className="text-indigo-500" />
                            <span>{moduleCount} Module{moduleCount === 1 ? '' : 's'}</span>
                          </div>
                        </div>

                        {/* Assigned Timetable Preview */}
                        {slots.length > 0 && (
                          <div className="p-2.5 bg-blue-50/60 rounded-lg border border-blue-100 text-[11px] text-blue-900 mt-2 space-y-1">
                            <span className="font-bold block flex items-center gap-1 text-blue-700">
                              <Clock size={12} /> Scheduled Teaching Slots:
                            </span>
                            {slots.slice(0, 2).map((s) => (
                              <div key={s.id} className="flex justify-between">
                                <span>{s.day} ({s.startTime} - {s.endTime})</span>
                                <span className="text-blue-600 font-medium">{s.room}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="p-6 pt-0 border-t border-gray-100 flex items-center justify-between gap-3 mt-4">
                      <button
                        onClick={() => navigate('/teacher/timetable')}
                        className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 cursor-pointer"
                      >
                        <Clock size={14} /> Adjust Schedule
                      </button>
                      <button
                        onClick={() => navigate(`/teacher/courses/${course.id}/builder`)}
                        className="px-3 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                      >
                        View Curriculum
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        // FEATURE 2: Courses Pending for Administrator's Approval
        <div>
          {pendingCourses.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-sm">
              <div className="w-16 h-16 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <Clock size={32} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">No Courses Pending Approval</h3>
              <p className="text-sm text-gray-500 max-w-md mx-auto mb-6">
                All your submitted courses have been reviewed, or you have not submitted any new courses for administrative approval yet.
              </p>
              <button
                onClick={() => navigate('/teacher/create-course')}
                className="px-5 py-2.5 bg-amber-600 text-white rounded-lg text-sm font-bold hover:bg-amber-700 transition-colors shadow-sm"
              >
                Submit a Course for Approval
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {pendingCourses.map((req) => (
                <div 
                  key={req.id} 
                  className="bg-white rounded-2xl border border-amber-200/80 shadow-sm hover:shadow-md transition-all overflow-hidden flex flex-col justify-between"
                >
                  <div>
                    <div className="h-44 w-full overflow-hidden relative bg-gray-100">
                      <img 
                        src={req.imageUrl || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&q=80'} 
                        alt={req.title} 
                        className="w-full h-full object-cover"
                      />
                      <span className="absolute top-3 right-3 px-2.5 py-0.5 rounded-full text-[11px] font-bold shadow-sm bg-amber-500 text-white flex items-center gap-1">
                        <Clock size={12} /> Awaiting Administrator Review
                      </span>
                    </div>

                    <div className="p-6 space-y-3">
                      <span className="text-xs font-semibold text-amber-600 uppercase tracking-wider">
                        {req.category || 'General'}
                      </span>
                      <h3 className="font-bold text-gray-900 text-lg leading-snug">{req.title}</h3>
                      <p className="text-xs text-gray-500 line-clamp-2">{req.description}</p>

                      <div className="flex items-center gap-4 pt-2 border-t border-gray-100 text-xs text-gray-600">
                        <div className="flex items-center gap-1.5 font-medium">
                          <Layers size={14} className="text-amber-500" />
                          <span>{req.modulesCount} Module{req.modulesCount === 1 ? '' : 's'}</span>
                        </div>
                        <span className="text-[11px] text-gray-400">
                          Submitted: {req.createdAt ? new Date(req.createdAt).toLocaleDateString() : 'Recently'}
                        </span>
                      </div>

                      {/* Default Timetable Attached */}
                      {req.defaultTimetable && (
                        <div className="p-3 bg-amber-50/70 rounded-xl border border-amber-200/60 text-xs text-amber-900 space-y-1 mt-2">
                          <span className="font-bold block flex items-center gap-1 text-amber-800">
                            <Clock size={13} /> Proposed Default Timetable:
                          </span>
                          <div className="flex justify-between text-[11px]">
                            <span>Class (&lt; 6 PM):</span>
                            <span className="font-semibold">{req.defaultTimetable.day} {req.defaultTimetable.lectureStart} - {req.defaultTimetable.lectureEnd}</span>
                          </div>
                          <div className="flex justify-between text-[11px]">
                            <span>Lab (&gt; 6:30 PM):</span>
                            <span className="font-semibold">{req.defaultTimetable.day} {req.defaultTimetable.practiceStart} - {req.defaultTimetable.practiceEnd}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="p-6 pt-0 border-t border-gray-100 flex items-center justify-between gap-3 mt-4">
                    <span className="text-xs text-amber-600 font-semibold flex items-center gap-1">
                      <Clock size={13} /> Pending Admin Approval
                    </span>
                    <button
                      onClick={() => navigate(`/teacher/courses/${req.id}/builder`)}
                      className="px-3 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-700 border border-gray-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                    >
                      Inspect Draft
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TeacherCourses;

