import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Users, Plus, Clock, CheckCircle, ArrowUpRight, BookMarked, Settings, Layers } from 'lucide-react';

const TeacherCourses = () => {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [studentCounts, setStudentCounts] = useState({});
  const [courseTimetables, setCourseTimetables] = useState([]);

  const userName = localStorage.getItem('userName') || 'Teacher';
  const userEmail = localStorage.getItem('userEmail') || 'teacher@lms.edu';
  const teacherId = localStorage.getItem('teacherId') || '1';

  // Base catalog of known courses and their primary handlers
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
      modules: 8,
      lessons: 32,
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
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    // 2. Load pending courses from this teacher
    const pending = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');

    const allCatalog = [...defaultCourses, ...approved];

    // Filter courses strictly handled by this logged-in teacher
    const lastName = userName.split(' ').pop();
    const handledCourses = allCatalog.filter(c => {
      if (c.teacherEmail && c.teacherEmail.toLowerCase() === userEmail.toLowerCase()) return true;
      if (c.instructor && (c.instructor === userName || c.instructor.includes(lastName))) return true;
      if (c.teacher && (c.teacher === userName || c.teacher.includes(lastName))) return true;
      return false;
    });

    // Also include any pending requests created by this teacher
    const myPending = pending.filter(p => p.teacherEmail?.toLowerCase() === userEmail.toLowerCase() || p.teacherName === userName);
    const combined = [...handledCourses];

    for (const p of myPending) {
      if (!combined.some(c => c.id === p.id || c.title === p.title)) {
        combined.push({
          id: p.id,
          title: p.title,
          category: p.category || 'General',
          instructor: userName,
          description: p.description || 'Under administrative review.',
          imageUrl: p.imageUrl || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&q=80',
          modules: p.modules?.length || 4,
          lessons: 16,
          status: 'Pending Admin Approval'
        });
      }
    }

    setCourses(combined);

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
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 flex items-center gap-1">
              <BookOpen size={12} /> Instructor Curriculum Management
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Courses Handled by {userName}</h1>
          <p className="text-gray-600 mt-1">
            View, manage, and inspect the courses assigned to and taught by you.
          </p>
        </div>

        <button
          onClick={() => navigate('/teacher/create-course')}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Plus size={18} /> Create New Course
        </button>
      </div>

      {/* Course Cards Grid */}
      {courses.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center shadow-sm">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <BookMarked size={32} />
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">No Courses Currently Handled</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto mb-6">
            You do not have any courses assigned to your profile yet. You can upload textbook material to generate a new AI course!
          </p>
          <button
            onClick={() => navigate('/teacher/create-course')}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors shadow-sm"
          >
            Create Course Now
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course) => {
            const enrolled = studentCounts[course.title] || (course.id === 101 ? 75 : course.id === 104 ? 42 : 12);
            const slots = courseTimetables.filter(t => t.courseTitle === course.title);

            return (
              <div 
                key={course.id} 
                className="bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow overflow-hidden flex flex-col justify-between"
              >
                <div>
                  <div className="h-44 w-full overflow-hidden relative bg-gray-100">
                    <img 
                      src={course.imageUrl} 
                      alt={course.title} 
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <span className={`absolute top-3 right-3 px-2.5 py-0.5 rounded-full text-[11px] font-bold shadow-sm ${
                      course.status === 'Pending Admin Approval'
                        ? 'bg-amber-500 text-white'
                        : 'bg-emerald-600 text-white'
                    }`}>
                      {course.status}
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
                        <span>{enrolled} Enrolled</span>
                      </div>
                      <div className="flex items-center gap-1.5 font-medium">
                        <Layers size={14} className="text-indigo-500" />
                        <span>{course.modules} Modules</span>
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
                    onClick={() => navigate('/teacher/courses/1/builder')}
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
  );
};

export default TeacherCourses;

