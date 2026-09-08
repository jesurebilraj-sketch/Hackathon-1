import React, { useState, useEffect } from 'react';
import { Target, BookOpen, Clock, Compass, Calendar, CheckCircle, ChevronRight, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const StudentDashboard = () => {
  const navigate = useNavigate();
  const userName = localStorage.getItem('userName') || 'Alex';

  // State for approved courses & enrolled approved courses
  const [enrolledApprovedCourses, setEnrolledApprovedCourses] = useState([]);
  const [availableApprovedCourses, setAvailableApprovedCourses] = useState([]);
  const [timetables, setTimetables] = useState([]);
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
          c.id === courseObj.id || 
          c.title?.toLowerCase() === courseObj.title?.toLowerCase()
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

    return () => {
      window.removeEventListener('storage', handleStorageUpdate);
      window.removeEventListener('approvedCoursesUpdated', handleStorageUpdate);
    };
  }, []);

  if (loading) return null;

  const hasEnrollments = enrolledApprovedCourses.length > 0;
  const currentCourse = hasEnrollments ? enrolledApprovedCourses[0] : null;

  // Find timetable sessions for enrolled approved courses
  const enrolledTimetableSlots = timetables.filter(t => 
    enrolledApprovedCourses.some(c => c.id === t.courseId || c.title === t.courseTitle)
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
                        <button
                          onClick={() => navigate(`/student/courses/${course.id}/teachers`)}
                          className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors shadow-sm flex items-center justify-center gap-1.5 cursor-pointer"
                        >
                          Enroll Now <ChevronRight size={16} />
                        </button>
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
                <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  <Calendar size={20} className="text-blue-600" /> Approved Course Timetable
                </h2>
                <span className="text-xs text-gray-500">Lectures before 6:00 PM • Practice after 6:30 PM</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {enrolledTimetableSlots.map((slot) => (
                  <div key={slot.id} className="p-3.5 rounded-lg border border-gray-200 bg-gray-50 flex items-start gap-3">
                    <div className="p-2 bg-white rounded border border-gray-200 text-center min-w-[55px]">
                      <span className="block text-xs font-bold text-blue-600 uppercase">{slot.day?.slice(0, 3)}</span>
                      <span className="block text-[10px] text-gray-500">{slot.type}</span>
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 text-sm">{slot.courseTitle}</h4>
                      <p className="text-xs text-gray-600">{slot.startTime} - {slot.endTime}</p>
                      <p className="text-[11px] text-gray-500 mt-0.5">Faculty: {slot.teacherName} • Room: {slot.room}</p>
                    </div>
                  </div>
                ))}
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
