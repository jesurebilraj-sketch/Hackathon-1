import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, BookOpen, CheckCircle } from 'lucide-react';

const CategoryCourses = () => {
  const { category } = useParams();
  const navigate = useNavigate();
  const decodedCategory = decodeURIComponent(category);

  const [courses, setCourses] = React.useState([]);
  const [enrolledIds, setEnrolledIds] = React.useState(new Set());
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchCategoryCourses = async () => {
      try {
        const userEmail = localStorage.getItem('userEmail') || 'default';
        const studentLocalEnrollments = JSON.parse(localStorage.getItem(`mockEnrollments_${userEmail}`) || '[]');
        const registeredSet = new Set(
          studentLocalEnrollments.map(e => String(e.course?.id || e.id))
        );
        const registeredTitleSet = new Set(
          studentLocalEnrollments.map(e => (e.course?.title || e.title || '').trim().toLowerCase())
        );
        setEnrolledIds({ ids: registeredSet, titles: registeredTitleSet });

        // Load administrator-approved courses strictly
        const adminApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
        const matchingApproved = adminApproved.filter(c => 
          c.category?.toLowerCase() === decodedCategory.toLowerCase()
        ).map(c => ({
          id: c.id,
          title: c.title,
          instructor: c.teacher || c.teacherName || 'Assigned Faculty',
          modules: c.modules?.length || 10,
          imageUrl: c.imageUrl || 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80'
        }));

        setCourses(matchingApproved);
      } catch (err) {
        console.warn("Failed to load category courses", err);
        setCourses([]);
      } finally {
        setLoading(false);
      }
    };
    fetchCategoryCourses();
  }, [decodedCategory]);

  return (
    <div className="max-w-6xl mx-auto pb-12">
      <button 
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-blue-600 mb-6 transition-colors cursor-pointer"
      >
        <ArrowLeft size={16} />
        Back to Courses
      </button>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Available {decodedCategory} Courses</h1>
        <p className="text-gray-600 mt-2">Explore the best courses handpicked for you in this category.</p>
      </div>

      {courses.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center text-gray-500">
          <BookOpen size={36} className="mx-auto mb-3 text-gray-400" />
          <h3 className="text-lg font-bold text-gray-800 mb-1">No Approved Courses in {decodedCategory}</h3>
          <p className="text-sm text-gray-500 max-w-md mx-auto">
            Currently, there are no administrator-approved courses available in this category. Check back after faculty proposals are reviewed and approved.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {courses.map(course => (
            <div key={course.id} className="group bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow flex flex-col">
              <div className="h-32 w-full overflow-hidden bg-gray-100">
                <img src={course.imageUrl} alt={course.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              </div>
              <div className="p-5 flex flex-col flex-1">
                <span className="text-xs font-semibold text-blue-600 tracking-wider uppercase mb-2">{decodedCategory}</span>
                <h4 className="font-bold text-gray-900 mb-2 flex-1 cursor-pointer hover:text-blue-600 transition-colors">{course.title}</h4>
                <p className="text-sm text-gray-500 mb-4 flex items-center gap-2">
                  <BookOpen size={14} />
                  {course.modules} Modules
                </p>
                {enrolledIds?.ids?.has(String(course.id)) || enrolledIds?.titles?.has(course.title?.trim().toLowerCase()) ? (
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
                    className="w-full py-2 bg-blue-50 border border-transparent rounded-lg text-sm font-medium text-blue-700 hover:bg-blue-600 hover:text-white transition-colors cursor-pointer"
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
  );
};

export default CategoryCourses;

