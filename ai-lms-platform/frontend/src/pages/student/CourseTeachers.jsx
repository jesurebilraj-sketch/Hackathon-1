import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Star, Calendar, Clock, BookOpen, CheckCircle } from 'lucide-react';
import { api } from '../../services/api';

const CourseTeachers = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [enrolling, setEnrolling] = useState(false);
  const [teacherStats, setTeacherStats] = useState(() => {
    const saved = localStorage.getItem('teacherStats');
    return saved ? JSON.parse(saved) : { 1: 0, 2: 0, 3: 0 };
  });

  // Mock data for available teachers and their specific lesson plans
  const defaultTeachers = [
    {
      id: 1,
      name: 'Dr. Alan Turing',
      email: 'alan.turing@lms.edu',
      avatar: 'https://ui-avatars.com/api/?name=Alan+Turing&background=0D8ABC&color=fff',
      rating: 4.9,
      students: teacherStats[1] || 0,
      style: 'Theoretical & Intensive',
      schedule: [
        { week: 1, title: 'Foundations & Theory', portions: ['Introduction to Core Concepts', 'Historical Context', 'Basic Syntax'] },
        { week: 2, title: 'Deep Dive into Modules', portions: ['Advanced Architectures', 'Memory Management', 'Algorithms 101'] },
        { week: 3, title: 'Practical Application', portions: ['Building the first project', 'Debugging Techniques'] },
        { week: 4, title: 'Final Assessments', portions: ['Comprehensive Review', 'Final Exam'] }
      ]
    },
    {
      id: 2,
      name: 'Prof. Grace Hopper',
      email: 'grace.hopper@lms.edu',
      avatar: 'https://ui-avatars.com/api/?name=Grace+Hopper&background=10B981&color=fff',
      rating: 4.8,
      students: teacherStats[2] || 0,
      style: 'Practical & Project-Based',
      schedule: [
        { week: 1, title: 'Fast-Track Basics', portions: ['Quick Setup', 'Syntax overview', 'First script'] },
        { week: 2, title: 'Real-World Projects', portions: ['API Integration', 'Database connections'] },
        { week: 3, title: 'Optimization', portions: ['Performance tuning', 'Code Refactoring'] },
        { week: 4, title: 'Deployment', portions: ['Cloud Hosting', 'CI/CD Pipelines'] }
      ]
    },
    {
      id: 3,
      name: 'Dr. Ada Lovelace',
      email: 'ada.lovelace@lms.edu',
      avatar: 'https://ui-avatars.com/api/?name=Ada+Lovelace&background=8B5CF6&color=fff',
      rating: 5.0,
      students: teacherStats[3] || 0,
      style: 'Paced & Beginner Friendly',
      schedule: [
        { week: 1, title: 'Gentle Introduction', portions: ['What is this course?', 'Setting up tools slowly'] },
        { week: 2, title: 'The Basics', portions: ['Variables and Types', 'Basic Logic'] },
        { week: 3, title: 'Intermediate Steps', portions: ['Functions', 'Simple Classes'] },
        { week: 4, title: 'Wrapping Up', portions: ['Mini-project', 'Course Review'] }
      ]
    }
  ];

  // Merge custom faculty added by Administrator and their assigned subjects
  const customFaculty = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
  const subjectAssignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');

  const mappedCustomFaculty = customFaculty.map(f => ({
    id: f.id,
    name: f.name,
    email: f.email,
    avatar: f.avatar,
    subject: subjectAssignments[f.id] || f.subject || f.department || 'Specialized Subject',
    rating: f.rating || 5.0,
    students: teacherStats[f.id] || 0,
    style: f.style || 'Interactive & Engaging',
    schedule: [
      { week: 1, title: 'Core Foundations', portions: ['Syllabus Overview', 'Key Principles', 'Initial Setup'] },
      { week: 2, title: 'Deep Modules & Architecture', portions: ['Theoretical Framework', 'Core Implementation'] },
      { week: 3, title: 'Applied Projects', portions: ['Industry Case Studies', 'Problem Sets'] },
      { week: 4, title: 'Capstone & Evaluation', portions: ['Project Review', 'Final Comprehensive Evaluation'] }
    ]
  }));

  const availableTeachers = [...defaultTeachers, ...mappedCustomFaculty];

  // Calculate enrolled courses count for 5-course restriction
  const userEmail = localStorage.getItem('userEmail') || 'default';
  const studentLocalEnrollments = JSON.parse(localStorage.getItem(`mockEnrollments_${userEmail}`) || '[]');
  const currentEnrollmentCount = studentLocalEnrollments.length;
  
  // Find active enrollment record for this specific course (if any)
  const existingEnrollment = studentLocalEnrollments.find(e => 
    String(e.course?.id) === String(id) || 
    String(e.id) === String(id) ||
    (course?.title && (e.course?.title || e.title) && (e.course?.title || e.title).trim().toLowerCase() === course.title.trim().toLowerCase())
  );
  const isAlreadyEnrolled = !!existingEnrollment;
  const enrolledFacultyName = existingEnrollment?.course?.teacher || existingEnrollment?.course?.teacherName || existingEnrollment?.teacher || existingEnrollment?.instructor;
  const isLimitReached = currentEnrollmentCount >= 5 && !isAlreadyEnrolled;

  // Load Course Timetables strictly for this approved course
  const allTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
  const courseTimetable = allTimetables.filter(t => t.courseId == id || t.courseTitle?.toLowerCase() === course?.title?.toLowerCase());

  const handleEnroll = async () => {
    if (isAlreadyEnrolled) {
      alert(`Enrollment Policy: You have already enrolled in this course with faculty ${enrolledFacultyName || 'an instructor'}. Institutional policy permits each student to enroll in a course only once under one faculty.`);
      navigate('/student/courses');
      return;
    }

    // 5-Course Limit Enforcement
    if (isLimitReached) {
      alert('Enrollment Limit Reached: Institutional academic policy restricts students to a maximum of 5 concurrent courses. You cannot enroll in additional courses.');
      return;
    }

    // Common enrollment persistence function to ensure student courses & teacher students sync seamlessly
    const persistEnrollment = () => {
      // Increment teacher student count for this teacher
      const newStats = { 
        ...teacherStats, 
        [selectedTeacher.id]: (teacherStats[selectedTeacher.id] || 0) + 1,
        [selectedTeacher.name]: ((teacherStats[selectedTeacher.name] || 0) + 1)
      };
      setTeacherStats(newStats);
      localStorage.setItem('teacherStats', JSON.stringify(newStats));

      // Resolve course details from approved courses
      const approvedCourses = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
      const matchedCourse = approvedCourses.find(c => String(c.id) === String(id)) || {
        id: id,
        title: `Course #${id}`,
        category: 'General',
        modules: []
      };

      const resolvedTitle = matchedCourse.title || `Course #${id}`;
      const resolvedCategory = matchedCourse.category || 'General';

      // 1. Scoped student mock enrollments
      const mockEnrollments = JSON.parse(localStorage.getItem(`mockEnrollments_${userEmail}`) || '[]');
      if (!mockEnrollments.find(e => (String(e.course?.id) === String(id) || String(e.id) === String(id)))) {
        mockEnrollments.push({
          enrollment_id: Date.now(),
          course: {
            id: id,
            title: resolvedTitle,
            category: resolvedCategory,
            teacher: selectedTeacher.name,
            teacherName: selectedTeacher.name,
            teacherId: selectedTeacher.id,
            teacherEmail: selectedTeacher.email,
            instructor: selectedTeacher.name,
            modules: matchedCourse.modules || [],
            imageUrl: matchedCourse.imageUrl || 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80'
          }
        });
        localStorage.setItem(`mockEnrollments_${userEmail}`, JSON.stringify(mockEnrollments));
      }

      // 2. Global teacher students list for the Teacher Portal demo (both by ID and email/name)
      const userName = localStorage.getItem('userName') || 'Demo Student';
      const teacherKeys = [
        `teacherStudents_${selectedTeacher.id}`,
        `teacherStudents_${selectedTeacher.name.replace(/\s+/g, '_')}`
      ];
      teacherKeys.forEach(tKey => {
        const mockTeacherStudents = JSON.parse(localStorage.getItem(tKey) || '[]');
        if (!mockTeacherStudents.find(s => (s.id === studentId || s.email === userEmail) && s.course === resolvedTitle)) {
          mockTeacherStudents.push({
            id: studentId,
            name: userName,
            email: userEmail,
            course: resolvedTitle,
            courseId: id,
            progress: 0,
            lastActive: 'Just now',
            modules: matchedCourse.modules || []
          });
          localStorage.setItem(tKey, JSON.stringify(mockTeacherStudents));
        }
      });

      // Also ensure the approved course object in approvedCourses stores the assigned teacher if not already set
      const updatedApprovedCourses = approvedCourses.map(c => {
        if (String(c.id) === String(id)) {
          return {
            ...c,
            teacher: c.teacher || selectedTeacher.name,
            teacherName: c.teacherName || selectedTeacher.name,
            teacherId: c.teacherId || selectedTeacher.id,
            teacherEmail: c.teacherEmail || selectedTeacher.email
          };
        }
        return c;
      });
      localStorage.setItem('approvedCourses', JSON.stringify(updatedApprovedCourses));

      // Notify other views and components that enrollments and approved courses have updated
      window.dispatchEvent(new Event('storage'));
      window.dispatchEvent(new Event('enrollmentsUpdated'));
      window.dispatchEvent(new Event('approvedCoursesUpdated'));
    };

    try {
      // Use the actual API!
      await api.enrollStudent(studentId, id, selectedTeacher.id);
      persistEnrollment();
      alert(`Successfully registered with ${selectedTeacher.name}!`);
      navigate('/student/courses');
    } catch (err) {
      console.warn("API failed, using mock success fallback.", err);
      persistEnrollment();
      alert(`Successfully registered with ${selectedTeacher.name}!`);
      navigate('/student/courses');
    } finally {
      setEnrolling(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto pb-12">
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-blue-600 mb-6 transition-colors cursor-pointer"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Available Teachers</h1>
        <p className="text-gray-600 mt-2">Select a teacher whose weekly lesson plan matches your learning style.</p>
        {isAlreadyEnrolled && (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-sm">
            <div className="flex items-center gap-3">
              <CheckCircle className="text-emerald-600 shrink-0" size={20} />
              <div>
                <span className="font-bold text-emerald-900">Enrolled Course Policy:</span>
                <span className="text-emerald-800 ml-1">
                  You are enrolled in this course under <strong>{enrolledFacultyName || 'your assigned faculty'}</strong>. A student can enroll in a course only once for only one faculty.
                </span>
              </div>
            </div>
            <button
              onClick={() => navigate('/student/courses')}
              className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 transition-colors shrink-0 ml-4 cursor-pointer"
            >
              View in My Courses
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: List of Teachers */}
        <div className="lg:col-span-1 space-y-4">
          {availableTeachers.map(teacher => {
            const isEnrolledWithThisTeacher = isAlreadyEnrolled && (
              teacher.name === enrolledFacultyName || 
              (enrolledFacultyName && (teacher.name.includes(enrolledFacultyName) || enrolledFacultyName.includes(teacher.name)))
            );

            return (
              <div 
                key={teacher.id}
                onClick={() => setSelectedTeacher(teacher)}
                className={`p-5 rounded-xl border-2 transition-all cursor-pointer flex items-start gap-4 relative ${
                  isEnrolledWithThisTeacher
                    ? 'border-emerald-500 bg-emerald-50/70 shadow-md ring-2 ring-emerald-300'
                    : selectedTeacher?.id === teacher.id 
                      ? 'border-blue-500 bg-blue-50 shadow-md' 
                      : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-gray-50'
                }`}
              >
                {isEnrolledWithThisTeacher && (
                  <span className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white flex items-center gap-1 shadow-xs">
                    <CheckCircle size={10} /> Enrolled Faculty
                  </span>
                )}
                <img src={teacher.avatar} alt={teacher.name} className="w-12 h-12 rounded-full shadow-sm" />
                <div className="flex-1">
                  <h3 className="font-bold text-gray-900">{teacher.name}</h3>
                  <p className="text-xs text-blue-600 mb-1">{teacher.email}</p>
                  <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                    <span className="flex items-center gap-1 text-amber-500 font-medium">
                      <Star size={14} className="fill-current" /> {teacher.rating}
                    </span>
                    <span>•</span>
                    <span>{teacher.students} students</span>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className="text-xs font-medium px-2 py-0.5 bg-blue-50 border border-blue-100 rounded-md text-blue-700">
                      {teacher.subject || 'Core Faculty'}
                    </span>
                    <span className="text-xs font-medium px-2 py-0.5 bg-white border border-gray-200 rounded-md text-gray-600">
                      {teacher.style}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Weekly Lesson Plan Details */}
        <div className="lg:col-span-2">
          {selectedTeacher ? (
            <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-8">
              <div className="flex items-center justify-between mb-8 border-b border-gray-100 pb-6">
                <div className="flex items-center gap-4">
                  <img src={selectedTeacher.avatar} alt={selectedTeacher.name} className="w-16 h-16 rounded-full ring-4 ring-blue-50" />
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">{selectedTeacher.name}</h2>
                    <p className="text-sm text-gray-500 mb-1">{selectedTeacher.email}</p>
                    <p className="text-blue-600 font-medium text-sm">{selectedTeacher.style}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <button 
                    onClick={handleEnroll}
                    disabled={enrolling || isLimitReached || isAlreadyEnrolled}
                    className={`px-6 py-3 font-bold rounded-xl transition-colors shadow-sm cursor-pointer flex items-center gap-2 ${
                      isAlreadyEnrolled
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300 cursor-default'
                        : isLimitReached
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {isAlreadyEnrolled ? (
                      <>
                        <CheckCircle size={18} className="text-emerald-600" />
                        Course Enrolled
                      </>
                    ) : isLimitReached 
                      ? 'Course Limit Reached (5/5)' 
                      : enrolling 
                        ? 'Enrolling...' 
                        : 'Confirm Enrollment'}
                  </button>
                  {isAlreadyEnrolled && (
                    <span className="text-xs font-semibold text-emerald-700">
                      You are actively studying this course
                    </span>
                  )}
                  {isLimitReached && (
                    <span className="text-xs font-semibold text-red-600">
                      Maximum 5 courses allowed per student
                    </span>
                  )}
                </div>
              </div>

              {/* Official Course Timetable configured by Administrator */}
              {courseTimetable.length > 0 && (
                <div className="mb-8 p-5 bg-gradient-to-r from-blue-50/70 to-purple-50/70 rounded-xl border border-blue-100">
                  <h3 className="text-base font-bold text-gray-900 flex items-center gap-2 mb-3">
                    <Clock className="text-blue-600" size={18} />
                    Official Course Timetable & Practice Sessions
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {courseTimetable.map((slot) => (
                      <div key={slot.id} className="p-3 bg-white rounded-lg border border-gray-200 text-xs shadow-2xs">
                        <div className="flex items-center justify-between mb-1">
                          <span className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                            slot.sessionType === 'class' 
                              ? 'bg-blue-100 text-blue-800' 
                              : 'bg-purple-100 text-purple-800'
                          }`}>
                            {slot.sessionType === 'class' ? 'Lecture (< 6 PM)' : 'Practice Lab (> 6:30 PM)'}
                          </span>
                          <span className="font-semibold text-gray-700">{slot.day}</span>
                        </div>
                        <div className="font-bold text-gray-900 text-sm mt-1">
                          {slot.startTime} – {slot.endTime}
                        </div>
                        <div className="text-gray-500 mt-0.5">
                          Venue: <span className="text-gray-700">{slot.room}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-6">
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-4">
                  <Calendar className="text-blue-500" size={20} />
                  Weekly Lesson Breakdown
                </h3>
                
                <div className="relative border-l-2 border-blue-100 ml-3 pl-6 space-y-8">
                  {selectedTeacher.schedule.map((week, idx) => (
                    <div key={idx} className="relative">
                      {/* Timeline Dot */}
                      <div className="absolute -left-[33px] top-1 h-4 w-4 rounded-full bg-blue-500 ring-4 ring-white"></div>
                      
                      <div className="bg-gray-50 border border-gray-100 rounded-xl p-5 hover:border-blue-200 transition-colors">
                        <div className="flex justify-between items-center mb-3">
                          <h4 className="font-bold text-gray-900 text-lg">Week {week.week}: {week.title}</h4>
                          <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded-full">Module {idx + 1}</span>
                        </div>
                        <ul className="space-y-2 mt-3">
                          {week.portions.map((portion, pIdx) => (
                            <li key={pIdx} className="flex items-start gap-2 text-gray-600 text-sm">
                              <CheckCircle size={16} className="text-emerald-500 mt-0.5 shrink-0" />
                              <span>{portion}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[400px] bg-gray-50 border-2 border-dashed border-gray-200 rounded-2xl flex flex-col items-center justify-center text-center p-8">
              <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center text-gray-400 mb-4">
                <BookOpen size={24} />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Select a Teacher</h3>
              <p className="text-gray-500 max-w-sm">
                Click on any teacher from the list to view their detailed weekly lesson plan and teaching style.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default CourseTeachers;

