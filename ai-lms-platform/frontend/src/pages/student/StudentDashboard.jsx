import React, { useState, useEffect } from 'react';
import { Target, BookOpen, Clock, Compass, Calendar, CheckCircle, ChevronRight, User, AlertTriangle, Bell, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const StudentDashboard = () => {
  const navigate = useNavigate();
  const userName = localStorage.getItem('userName') || 'Alex';

  // State for approved courses & enrolled approved courses
  const [enrolledApprovedCourses, setEnrolledApprovedCourses] = useState([]);
  const [availableApprovedCourses, setAvailableApprovedCourses] = useState([]);
  const [timetables, setTimetables] = useState([]);
  const [rescheduledClasses, setRescheduledClasses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      const userEmail = localStorage.getItem('userEmail') || 'default';
      const studentId = parseInt(localStorage.getItem('studentId') || '1');

      // 1. Get live Administrator Approved Courses
      const approvedList = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
      setAvailableApprovedCourses(approvedList);

      // 2. Load scheduled timetables (lectures before 6pm, practice after 6:30pm)
      const allTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
      setTimetables(allTimetables);

      // 3. Load Rescheduled Classes from Faculty
      const allRescheduled = JSON.parse(localStorage.getItem('rescheduledClasses') || '[]');
      setRescheduledClasses(allRescheduled);

      // 3. Fetch enrollments
      let apiEnrollments = [];
      try {
        const { api } = await import('../../services/api');
        const data = await api.getStudentEnrollments(studentId);
        if (data && data.enrollments) {
          apiEnrollments = data.enrollments;
        }
      } catch (error) {
        console.warn("Failed to fetch API enrollments.", error);
      }

      const mockEnrollments = JSON.parse(localStorage.getItem(`mockEnrollments_${userEmail}`) || '[]');
      const combined = [...apiEnrollments, ...mockEnrollments];

      // 4. Strict filter: ONLY courses that are approved by the administrator
      const filtered = [];
      for (const enr of combined) {
        const courseObj = enr.course || enr;
        const matchingApproved = approvedList.find(c => 
          String(c.id) === String(courseObj.id) || 
          (c.title && courseObj.title && c.title.trim().toLowerCase() === courseObj.title.trim().toLowerCase())
        );
        if (matchingApproved) {
          // Attach approved course details (instructor, modules, etc.)
          filtered.push({
            ...matchingApproved,
            enrollmentId: enr.enrollment_id || enr.id,
            progress: enr.progress || 0,
            instructor: matchingApproved.teacher || matchingApproved.teacherName || courseObj.teacher || 'Assigned Faculty'
          });
        }
      }

      setEnrolledApprovedCourses(filtered);
      setLoading(false);
    };

    loadDashboardData();

    // Listen to local storage changes across tabs or window events
    const handleStorageUpdate = () => loadDashboardData();
    window.addEventListener('storage', handleStorageUpdate);
    window.addEventListener('approvedCoursesUpdated', handleStorageUpdate);
    window.addEventListener('rescheduledClassesUpdated', handleStorageUpdate);

    return () => {
      window.removeEventListener('storage', handleStorageUpdate);
      window.removeEventListener('approvedCoursesUpdated', handleStorageUpdate);
      window.removeEventListener('rescheduledClassesUpdated', handleStorageUpdate);
    };
  }, []);

  if (loading) return null;

  const hasEnrollments = enrolledApprovedCourses.length > 0;
  const currentCourse = hasEnrollments ? enrolledApprovedCourses[0] : null;

  // Find timetable sessions for enrolled approved courses
  const enrolledTimetableSlots = timetables.filter(t => 
    enrolledApprovedCourses.some(c => c.id === t.courseId || c.title === t.courseTitle)
  );

  // Find rescheduled classes relevant to student's enrolled courses or all approved courses if browsing
  const activeReschedulesForEnrolled = rescheduledClasses.filter(r => 
    enrolledApprovedCourses.some(c => c.id === r.courseId || c.title?.toLowerCase() === r.courseTitle?.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Good Morning, {userName} 👋</h1>
          <p className="text-gray-600 mt-1">
            {hasEnrollments
              ? `You are enrolled in ${enrolledApprovedCourses.length} Administrator-Approved course${enrolledApprovedCourses.length > 1 ? 's' : ''} (Max 5 allowed).`
              : 'Welcome to AI-LMS! Browse curriculum approved by the academic administrator.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full text-xs font-semibold">
            Enrolled: {enrolledApprovedCourses.length} / 5 Max
          </span>
          <button
            onClick={() => navigate('/student/courses')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm flex items-center gap-1.5 cursor-pointer"
          >
            <BookOpen size={16} /> Available Courses
          </button>
        </div>
      </div>

      {/* Rescheduled Class Alert Banner for Students */}
      {activeReschedulesForEnrolled.length > 0 && (
        <div className="bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 rounded-2xl p-6 text-white shadow-lg space-y-4 animate-in fade-in slide-in-from-top-4 duration-300">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2.5 bg-white/20 backdrop-blur-md rounded-xl">
                <Bell size={22} className="text-white animate-bounce" />
              </div>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider bg-white/20 px-2 py-0.5 rounded-full inline-block mb-1">
                  Urgent Faculty Notification
                </span>
                <h2 className="text-xl font-bold">Class Schedule Notice from Your Faculty</h2>
              </div>
            </div>
            <span className="text-xs font-semibold px-3 py-1 bg-white/20 backdrop-blur-md rounded-full">
              {activeReschedulesForEnrolled.length} Rescheduled Class{activeReschedulesForEnrolled.length > 1 ? 'es' : ''}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            {activeReschedulesForEnrolled.map((reschedule) => (
              <div key={reschedule.id} className="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/25 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-xs font-bold text-amber-100 uppercase tracking-wide block">
                      {reschedule.sessionType === 'class' ? 'Course Lecture' : 'Practice Lab'}
                    </span>
                    <h3 className="font-bold text-base text-white">{reschedule.courseTitle}</h3>
                    <p className="text-xs text-amber-100 mt-0.5">Faculty: {reschedule.teacherName}</p>
                  </div>
                  <span className="px-2 py-0.5 bg-amber-300 text-amber-950 font-bold rounded text-[10px] uppercase">
                    Rescheduled
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs bg-black/15 p-2.5 rounded-lg border border-white/10">
                  <div>
                    <span className="text-amber-200 block text-[10px] uppercase">Original Schedule</span>
                    <span className="line-through text-amber-100">
                      {reschedule.originalDay}, {reschedule.originalStartTime} - {reschedule.originalEndTime}
                    </span>
                  </div>
                  <div>
                    <span className="text-emerald-300 font-bold block text-[10px] uppercase">New Schedule</span>
                    <span className="text-white font-bold">
                      {reschedule.newDay} ({reschedule.newDate}), {reschedule.newStartTime} - {reschedule.newEndTime}
                    </span>
                  </div>
                </div>

                <div className="bg-white/15 p-2.5 rounded-lg border border-white/15 text-xs">
                  <p className="font-semibold text-amber-200 flex items-center gap-1 text-[11px] mb-0.5">
                    <MessageSquare size={12} /> Instructor's Message:
                  </p>
                  <p className="italic text-white">"{reschedule.message}"</p>
                  <p className="text-[10px] text-amber-200 mt-1 font-medium">Room / Link: {reschedule.room}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasEnrollments ? (
        // Empty State: No Approved Courses Enrolled Yet
        <div className="space-y-6">
          <div className="bg-white p-10 rounded-xl border border-gray-200 shadow-sm flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-4">
              <Compass size={32} />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">No Approved Courses Enrolled</h2>
            <p className="text-gray-500 max-w-md mb-6 text-sm">
              Your dashboard only displays courses verified and approved by the academic administrator. Choose an approved course below to begin your studies.
            </p>
            <button 
              onClick={() => navigate('/student/courses')}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 shadow-sm flex items-center gap-2 transition-colors cursor-pointer text-sm"
            >
              <BookOpen size={18} />
              Browse All Available Courses
            </button>
          </div>

          {/* List of Administrator-Approved Courses Available for Enrollment */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold text-gray-900">Administrator-Approved Courses</h2>
                <p className="text-xs text-gray-500">Official curriculum cleared by administration, ready for enrollment.</p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                {availableApprovedCourses.length} Approved Courses
              </span>
            </div>

            {availableApprovedCourses.length === 0 ? (
              <div className="bg-gray-50 rounded-xl border border-gray-200 p-8 text-center text-gray-500 text-sm">
                No courses have been approved by the administrator yet. Once faculty submit courses with their default timetables and the administrator approves them, they will appear here.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {availableApprovedCourses.map((course) => {
                  const courseSchedule = timetables.filter(t => t.courseId === course.id || t.courseTitle === course.title);
                  return (
                    <div key={course.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                      <div>
                        <div className="h-32 w-full overflow-hidden bg-gray-100">
                          <img 
                            src={course.imageUrl || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&q=80'} 
                            alt={course.title} 
                            className="w-full h-full object-cover" 
                          />
                        </div>
                        <div className="p-5">
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">{course.category || 'General'}</span>
                            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">Admin Approved</span>
                          </div>
                          <h3 className="font-bold text-gray-900 text-base mb-2 line-clamp-1">{course.title}</h3>
                          <p className="text-xs text-gray-600 line-clamp-2 mb-3">{course.description || 'Verified academic syllabus.'}</p>
                          
                          <div className="text-xs text-gray-600 space-y-1 bg-gray-50 p-2.5 rounded-lg border border-gray-100 mb-3">
                            <p className="flex items-center gap-1.5 font-medium text-gray-800">
                              <User size={13} className="text-blue-600" /> Instructor: {course.teacher || course.teacherName || 'Assigned Faculty'}
                            </p>
                            {courseSchedule.length > 0 ? (
                              <div className="pt-1 text-indigo-900 font-medium">
                                <span className="flex items-center gap-1">
                                  <Calendar size={13} className="text-indigo-600" /> 
                                  {courseSchedule[0].day} • {courseSchedule[0].startTime} - {courseSchedule[0].endTime}
                                </span>
                              </div>
                            ) : (
                              <p className="text-gray-400 italic">Schedule: Default timetable configured</p>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="p-5 pt-0">
                        {enrolledApprovedCourses.some(e => String(e.id) === String(course.id) || (e.title && course.title && e.title.trim().toLowerCase() === course.title.trim().toLowerCase())) ? (
                          <button
                            disabled
                            className="w-full py-2 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-sm font-semibold flex items-center justify-center gap-1.5 cursor-default"
                          >
                            <CheckCircle size={16} className="text-emerald-600" /> Course Enrolled
                          </button>
                        ) : (
                          <button
                            onClick={() => navigate(`/student/courses/${course.id}/teachers`)}
                            className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
                          >
                            Enroll Now <ChevronRight size={16} />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        // Active Enrolled State: Displays ONLY Approved Courses
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded mb-1 inline-block">
                    Administrator-Approved
                  </span>
                  <h2 className="text-lg font-bold text-gray-900">{currentCourse.title}</h2>
                  <p className="text-sm text-gray-500">Instructor: {currentCourse.instructor} • {currentCourse.category}</p>
                </div>
                <div className="text-right">
                  <span className="text-2xl font-bold text-blue-600">{currentCourse.progress}%</span>
                  <p className="text-sm text-gray-500">Overall Progress</p>
                </div>
              </div>
              
              <div className="w-full bg-gray-100 rounded-full h-2.5 mb-6">
                <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${currentCourse.progress}%` }}></div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg flex items-center justify-between border border-blue-100">
                <div>
                  <p className="text-sm font-medium text-blue-800 mb-1">Approved Curriculum</p>
                  <h3 className="font-bold text-blue-900">
                    {currentCourse.modules && currentCourse.modules.length > 0 
                      ? (currentCourse.modules[0].title || currentCourse.modules[0].name || 'Module 1: Foundations')
                      : 'Module 1: Introduction'}
                  </h3>
                  <p className="text-sm text-blue-700">Official syllabus approved by Administration</p>
                </div>
                <button 
                  onClick={() => navigate('/student/courses')}
                  className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm cursor-pointer"
                >
                  Continue Course
                </button>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-start gap-4">
                <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center shrink-0">
                  <Target size={24} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500">Enrolled Approved Courses</h3>
                  <p className="text-2xl font-bold text-gray-900 mt-1">{enrolledApprovedCourses.length} / 5</p>
                </div>
              </div>
              
              <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex items-start gap-4">
                <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center shrink-0">
                  <CheckCircle size={24} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-gray-500">Accreditation Status</h3>
                  <p className="text-lg font-bold text-emerald-700 mt-1">Admin Verified</p>
                </div>
              </div>
            </div>
          </div>

          {/* Enrolled Courses List */}
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-4">Your Enrolled Approved Courses</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {enrolledApprovedCourses.map((c) => {
                const courseSessions = timetables.filter(t => t.courseId === c.id || t.courseTitle === c.title);
                return (
                  <div key={c.id} className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                          {c.category}
                        </span>
                        <span className="text-xs font-bold text-emerald-600">Approved</span>
                      </div>
                      <h3 className="font-bold text-gray-900 mb-1">{c.title}</h3>
                      <p className="text-xs text-gray-600 mb-3">Faculty: {c.instructor}</p>

                      {courseSessions.length > 0 && (
                        <div className="p-2.5 bg-gray-50 border border-gray-100 rounded-lg text-xs space-y-1 mb-3">
                          <p className="font-semibold text-gray-700 flex items-center gap-1">
                            <Clock size={12} className="text-blue-600" /> Weekly Timetable:
                          </p>
                          {courseSessions.map((s, idx) => (
                            <p key={idx} className="text-gray-600">
                              {s.day}: <span className="font-medium">{s.startTime} - {s.endTime}</span> ({s.type})
                            </p>
                          ))}
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => navigate('/student/courses')}
                      className="w-full py-2 bg-gray-50 hover:bg-blue-50 text-gray-700 hover:text-blue-600 border border-gray-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                    >
                      View Modules & Study Plan
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Timetable Schedule from Approved Courses */}
          {enrolledTimetableSlots.length > 0 && (
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                    <Calendar size={20} className="text-blue-600" /> Approved Course Timetable
                  </h2>
                  <p className="text-xs text-gray-500">Official schedule approved by administrator with live faculty reschedule updates.</p>
                </div>
                <span className="text-xs text-gray-500">Lectures before 6:00 PM • Practice after 6:30 PM</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {enrolledTimetableSlots.map((slot) => {
                  const activeReschedule = rescheduledClasses.find(r => 
                    r.slotId === slot.id || 
                    (r.courseId === slot.courseId && r.sessionType === slot.sessionType && r.originalDay === slot.day)
                  );

                  return (
                    <div 
                      key={slot.id} 
                      className={`p-4 rounded-xl border flex flex-col justify-between ${
                        activeReschedule
                          ? 'border-amber-300 bg-amber-50/50 shadow-2xs'
                          : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                            slot.sessionType === 'practice' || slot.type === 'practice'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {slot.sessionType === 'practice' || slot.type === 'practice' ? 'Lab (> 6:30 PM)' : 'Lecture (< 6 PM)'}
                          </span>

                          {activeReschedule ? (
                            <span className="px-2 py-0.5 bg-amber-200 text-amber-900 font-bold rounded text-[10px] flex items-center gap-1">
                              <AlertTriangle size={11} /> Rescheduled
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium text-gray-500">
                              Default Timetable
                            </span>
                          )}
                        </div>

                        <h4 className="font-bold text-gray-900 text-sm mb-1">{slot.courseTitle}</h4>

                        {activeReschedule ? (
                          <div className="space-y-2 mt-2">
                            <div className="p-2 bg-white/90 rounded border border-amber-200 text-xs">
                              <p className="text-gray-400 line-through text-[11px]">
                                Default: {slot.day}, {slot.startTime} - {slot.endTime}
                              </p>
                              <p className="font-bold text-amber-900 text-xs mt-0.5">
                                Rescheduled: {activeReschedule.newDay} ({activeReschedule.newDate})
                              </p>
                              <p className="font-semibold text-amber-800 text-xs">
                                {activeReschedule.newStartTime} - {activeReschedule.newEndTime}
                              </p>
                            </div>

                            <div className="p-2 bg-amber-100/70 rounded border border-amber-200 text-xs text-amber-900">
                              <p className="font-bold flex items-center gap-1 text-[11px] mb-0.5">
                                <MessageSquare size={11} /> Note from Faculty:
                              </p>
                              <p className="italic text-[11px]">"{activeReschedule.message}"</p>
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs text-gray-600 mt-1 space-y-0.5">
                            <p className="font-semibold text-gray-800">{slot.day} • {slot.startTime} - {slot.endTime}</p>
                            <p className="text-[11px] text-gray-500">Room: {slot.room}</p>
                          </div>
                        )}
                      </div>

                      <div className="mt-3 pt-2 border-t border-gray-200/60 text-[11px] text-gray-500 flex items-center justify-between">
                        <span>Faculty: <strong className="text-gray-700">{slot.instructor || slot.teacherName || 'Faculty'}</strong></span>
                        {activeReschedule && (
                          <span className="text-amber-700 font-semibold">{activeReschedule.room}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Newly Approved Courses Available for Enrollment */}
          {availableApprovedCourses.filter(ac => !enrolledApprovedCourses.some(ec => ec.id === ac.id || ec.title?.toLowerCase() === ac.title?.toLowerCase())).length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-gray-900">Newly Approved Courses in Catalog</h2>
                  <p className="text-xs text-gray-500">Recently verified and approved by the academic administrator.</p>
                </div>
                <button
                  onClick={() => navigate('/student/courses')}
                  className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  View Full Catalog &rarr;
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {availableApprovedCourses
                  .filter(ac => !enrolledApprovedCourses.some(ec => ec.id === ac.id || ec.title?.toLowerCase() === ac.title?.toLowerCase()))
                  .slice(0, 3)
                  .map((course) => (
                    <div key={course.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                      <div>
                        <div className="h-32 w-full overflow-hidden bg-gray-100">
                          <img 
                            src={course.imageUrl || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&q=80'} 
                            alt={course.title} 
                            className="w-full h-full object-cover" 
                          />
                        </div>
                        <div className="p-4">
                          <div className="flex items-center justify-between gap-2 mb-1.5">
                            <span className="text-xs font-bold text-blue-600 uppercase tracking-wider">{course.category || 'General'}</span>
                            <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">Admin Approved</span>
                          </div>
                          <h3 className="font-bold text-gray-900 text-base mb-1 line-clamp-1">{course.title}</h3>
                          <p className="text-xs text-gray-600 line-clamp-2 mb-2">{course.description}</p>
                          <p className="text-xs text-gray-500">Faculty: <strong className="text-gray-700">{course.teacher || course.teacherName || 'Assigned Faculty'}</strong></p>
                        </div>
                      </div>

                      <div className="p-4 pt-0">
                        <button
                          onClick={() => navigate(`/student/courses/${course.id}/teachers`)}
                          className="w-full py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
                        >
                          Enroll in Course <ChevronRight size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default StudentDashboard;
