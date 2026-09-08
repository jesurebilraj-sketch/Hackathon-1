import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, PlayCircle, CheckCircle, Search, Compass } from 'lucide-react';

const StudentCourses = () => {
  const navigate = useNavigate();
  const [isNewUser, setIsNewUser] = useState(true);
  const [availableCourses, setAvailableCourses] = useState([]);
  const [enrolledCourses, setEnrolledCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    const fetchData = async () => {
      let apiEnrollments = [];
      const studentId = parseInt(localStorage.getItem('studentId') || '1');
      const userEmail = localStorage.getItem('userEmail') || 'default';
      
      try {
        const { api } = await import('../../services/api');
        
        // Strictly load Administrator-Approved courses
        const adminApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
        setAvailableCourses(adminApproved);

        // Fetch user enrollments dynamically
        const enrollmentsData = await api.getStudentEnrollments(studentId);
        if (enrollmentsData && enrollmentsData.enrollments) {
          apiEnrollments = enrollmentsData.enrollments;
        }
      } catch (error) {
        console.warn("Backend API unavailable, using local approved courses.", error);
        const adminApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
        setAvailableCourses(adminApproved);
      } finally {
        const mockLocalEnrollments = JSON.parse(localStorage.getItem(`mockEnrollments_${userEmail}`) || '[]');
        const combinedEnrollments = [...apiEnrollments, ...mockLocalEnrollments];

        // Filter enrolled courses so that ONLY administrator-approved courses appear
        const approvedOnlyEnrollments = combinedEnrollments.filter(enr => {
          const cId = enr.course ? enr.course.id : enr.id;
          const cTitle = enr.course ? enr.course.title : enr.title;
          return adminApproved.some(ac => 
            String(ac.id) === String(cId) || 
            (ac.title && cTitle && ac.title.trim().toLowerCase() === cTitle.trim().toLowerCase())
          );
        });

        if (approvedOnlyEnrollments.length > 0) {
          // Map backend/mock enrollments to frontend model
          const mappedEnrollments = approvedOnlyEnrollments.map(enr => {
            const cId = enr.course ? enr.course.id : enr.id;
            const cTitle = enr.course ? enr.course.title : enr.title;
            const matchedAc = adminApproved.find(ac => 
              String(ac.id) === String(cId) || 
              (ac.title && cTitle && ac.title.trim().toLowerCase() === cTitle.trim().toLowerCase())
            );

            return {
              id: cId,
              title: matchedAc ? matchedAc.title : cTitle,
              instructor: matchedAc?.teacher || matchedAc?.teacherName || (enr.course ? enr.course.teacher : enr.instructor) || 'Assigned Faculty',
              progress: enr.progress || 0,
              totalModules: matchedAc?.modules?.length || 10,
              completedModules: 0,
              lastAccessed: 'Just now',
              imageUrl: matchedAc?.imageUrl || (enr.course && enr.course.imageUrl) || 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80'
            };
          });
          setEnrolledCourses(mappedEnrollments);
          setIsNewUser(false);
        } else {
          setEnrolledCourses([]);
          setIsNewUser(true);
        }
        setLoading(false);
      }
    };

    fetchData();

    const handleUpdate = () => fetchData();
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('approvedCoursesUpdated', handleUpdate);
    window.addEventListener('enrollmentsUpdated', handleUpdate);

    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('approvedCoursesUpdated', handleUpdate);
      window.removeEventListener('enrollmentsUpdated', handleUpdate);
    };
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div className="flex justify-between items-center mb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">My Courses</h1>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
              enrolledCourses.length >= 5 
                ? 'bg-red-100 text-red-700 border border-red-200' 
                : 'bg-blue-50 text-blue-700 border border-blue-100'
            }`}>
              Capacity: {enrolledCourses.length} / 5 Max Courses
            </span>
          </div>
          <p className="text-gray-600 mt-1">
            Manage and track your enrolled courses. Institutional policy restricts students to 5 courses max.
          </p>
        </div>
        
        {/* Demo Toggle - Just for hackathon presentation purposes */}
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

      {/* Empty State / Browse Prompt if no courses registered */}
      {enrolledCourses.length === 0 && (
        <div className="bg-white p-12 rounded-xl border border-gray-200 shadow-sm flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mb-6">
            <Compass size={40} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">You haven't registered for any courses</h2>
          <p className="text-gray-500 max-w-md mb-8">
            Browse our catalog of administrator-approved courses below to begin your learning journey.
          </p>
        </div>
      )}

      {/* Active Courses (show whenever student has enrolled courses) */}
      {enrolledCourses.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Continue Learning</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {enrolledCourses.map(course => (
              <div key={course.id} className="group bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col">
                <div className="h-32 w-full overflow-hidden bg-gray-100">
                  <img src={course.imageUrl} alt={course.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                </div>
                <div className="p-6 flex flex-col flex-1">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-gray-900 line-clamp-2">{course.title}</h3>
                    <p className="text-sm text-gray-500 mt-1">{course.instructor}</p>
                    
                    <div className="mt-6">
                      <div className="flex justify-between items-end mb-2">
                        <span className="text-sm font-medium text-gray-700">{course.progress}% Complete</span>
                        <span className="text-xs text-gray-500">{course.completedModules}/{course.totalModules} Modules</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${course.progress === 100 ? 'bg-emerald-500' : 'bg-blue-600'}`} 
                          style={{ width: `${course.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-6 pt-6 border-t border-gray-100 flex items-center justify-between">
                    <span className="text-xs text-gray-400">Last active: {course.lastAccessed}</span>
                    <button className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800 cursor-pointer">
                      {course.progress === 0 ? 'Start' : course.progress === 100 ? 'Review' : 'Continue'} 
                      <PlayCircle size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-gray-200 pt-8 mt-8"></div>

      {/* Available Subjects */}
      <div className="mb-12">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Available Subjects</h3>
        <div className="flex flex-wrap gap-3">
          {[
            "Web Development", "Mathematics", "History", "Physics", "Computer Science", 
            "Biology", "Chemistry", "Data Science", "Machine Learning", "Art History", 
            "Literature", "Philosophy", "Economics", "Psychology", "Sociology", 
            "Business", "Marketing", "Design", "Cybersecurity", "Networking", "Languages"
          ].map((subject, idx) => (
            <button 
              key={idx}
              onClick={() => navigate(`/student/courses/category/${encodeURIComponent(subject)}`)}
              className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-full text-sm font-medium text-gray-700 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-colors cursor-pointer"
            >
              {subject}
            </button>
          ))}
        </div>
      </div>

      {/* Available Courses */}
      <div>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900">Trending Courses</h3>
          <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
            Admin Approved Catalog ({availableCourses.length})
          </span>
        </div>
        
        {availableCourses.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center text-gray-500">
            <BookOpen size={32} className="mx-auto mb-2 text-gray-400" />
            <p className="font-semibold text-gray-700">No Approved Courses Available Yet</p>
            <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
              Only courses verified and approved by the academic administrator appear in this catalog. Courses submitted by teachers will appear here as soon as they are approved.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {availableCourses.map(course => (
              <div key={course.id} className="group bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow flex flex-col">
                <div className="h-32 w-full overflow-hidden bg-gray-100">
                  <img src={course.imageUrl} alt={course.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                </div>
                <div className="p-5 flex flex-col flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <span 
                      onClick={() => navigate(`/student/courses/category/${encodeURIComponent(course.category)}`)}
                      className="text-xs font-semibold text-blue-600 tracking-wider uppercase cursor-pointer hover:underline"
                    >
                      {course.category}
                    </span>
                    <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                      Approved
                    </span>
                  </div>
                  <h4 className="font-bold text-gray-900 mb-4 flex-1 cursor-pointer hover:text-blue-600 transition-colors">{course.title}</h4>
                  {enrolledCourses.some(e => String(e.id) === String(course.id) || (e.title && course.title && e.title.trim().toLowerCase() === course.title.trim().toLowerCase())) ? (
                    <button 
                      disabled
                      className="w-full py-2 bg-emerald-50 border border-emerald-200 rounded-lg text-sm font-semibold text-emerald-700 flex items-center justify-center gap-1.5 cursor-default"
                    >
                      <CheckCircle size={16} className="text-emerald-600" />
                      Course Enrolled
                    </button>
                  ) : (
                    <button 
                      onClick={() => navigate(`/student/courses/${course.id}/teachers`)}
                      className="w-full py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-blue-600 hover:border-blue-300 transition-colors cursor-pointer"
                    >
                      Register Course
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentCourses;

