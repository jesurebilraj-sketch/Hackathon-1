import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, BookOpen } from 'lucide-react';

const CategoryCourses = () => {
  const { category } = useParams();
  const navigate = useNavigate();
  const decodedCategory = decodeURIComponent(category);

  const [courses, setCourses] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  // Fallback if DB is empty
  const getMockCourses = (cat) => {
    // Generate a consistent pseudo-random number based on the category string length
    // to pick different Unsplash images so categories look distinct.
    const seed = cat.length;
    const images = [
      'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80',
      'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80',
      'https://images.unsplash.com/photo-1555949963-aa79dcee981c?w=500&q=80',
      'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=500&q=80',
      'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=500&q=80',
      'https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=500&q=80',
      'https://images.unsplash.com/photo-1636466497217-26a8cbeaf0aa?w=500&q=80',
      'https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=500&q=80'
    ];

    // Check if Administrator appointed a specific teacher for this subject
    const customFaculty = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const assignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');
    
    // Find any teacher assigned to this category/subject
    const assignedTeachers = customFaculty.filter(f => f.subject === cat || assignments[f.id] === cat);
    const primaryTeacherName = assignedTeachers.length > 0 ? assignedTeachers[0].name : 'Dr. Alan Turing';

    return [
      {
        id: `mock-1`,
        title: `Introduction to ${cat}`,
        instructor: primaryTeacherName,
        modules: 12,
        imageUrl: images[(seed) % images.length]
      },
      {
        id: `mock-2`,
        title: `Advanced ${cat} Patterns`,
        instructor: assignedTeachers.length > 1 ? assignedTeachers[1].name : 'Prof. Grace Hopper',
        modules: 18,
        imageUrl: images[(seed + 1) % images.length]
      },
      {
        id: `mock-3`,
        title: `${cat} for Beginners`,
        instructor: primaryTeacherName,
        modules: 8,
        imageUrl: images[(seed + 2) % images.length]
      },
      {
        id: `mock-4`,
        title: `Mastering ${cat}`,
        instructor: 'Dr. Ada Lovelace',
        modules: 24,
        imageUrl: images[(seed + 3) % images.length]
      }
    ];
  };

  React.useEffect(() => {
    const fetchCategoryCourses = async () => {
      try {
        const { api } = await import('../../services/api');
        const data = await api.getAllCourses(decodedCategory);
        if (data.courses && data.courses.length > 0) {
          setCourses(data.courses.map(c => ({
            id: c.id,
            title: c.title,
            instructor: 'Expert Instructor',
            modules: 10, // Mock module count since we aren't joining modules yet
            imageUrl: c.imageUrl || 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80'
          })));
        } else {
          setCourses(getMockCourses(decodedCategory));
        }
      } catch (err) {
        console.warn("Backend unavailable, using mock data", err);
        setCourses(getMockCourses(decodedCategory));
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
              <button 
                onClick={() => navigate(`/student/courses/${course.id}/teachers`)}
                className="w-full py-2 bg-blue-50 border border-transparent rounded-lg text-sm font-medium text-blue-700 hover:bg-blue-600 hover:text-white transition-colors cursor-pointer"
              >
                Register Course
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CategoryCourses;

