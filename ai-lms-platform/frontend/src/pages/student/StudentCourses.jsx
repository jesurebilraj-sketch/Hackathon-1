import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, PlayCircle, CheckCircle, Search, Compass } from 'lucide-react';

const StudentCourses = () => {
  const navigate = useNavigate();
  const [isNewUser, setIsNewUser] = useState(true);
  const [availableCourses, setAvailableCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fallback Mock Data
  const mockMyCourses = [
    {
      id: 1, title: 'Python Programming Masterclass', instructor: 'AI Generated', progress: 78,
      totalModules: 12, completedModules: 9, lastAccessed: '2 hours ago',
      imageUrl: 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80'
    },
    {
      id: 2, title: 'Introduction to Data Structures', instructor: 'AI Generated', progress: 34,
      totalModules: 8, completedModules: 3, lastAccessed: '1 day ago',
      imageUrl: 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80'
    }
  ];

  const mockAvailableCourses = [
    { id: 101, title: 'Advanced React Patterns', category: 'Web Development', imageUrl: 'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=500&q=80' },
    { id: 102, title: 'Calculus I', category: 'Mathematics', imageUrl: 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=500&q=80' },
    { id: 103, title: 'World History: 20th Century', category: 'History', imageUrl: 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?w=500&q=80' },
    { id: 104, title: 'Physics for Engineers', category: 'Science', imageUrl: 'https://images.unsplash.com/photo-1636466497217-26a8cbeaf0aa?w=500&q=80' },
  ];

  React.useEffect(() => {
    const fetchCourses = async () => {
      try {
        const { api } = await import('../../services/api');
        const data = await api.getAllCourses();
        if (data.courses && data.courses.length > 0) {
          // Map backend data to frontend model
          setAvailableCourses(data.courses.map(c => ({
            id: c.id,
            title: c.title,
            category: 'AI Generated', // Fallback since DB doesn't have category yet
            imageUrl: 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80'
          })));
        } else {
          setAvailableCourses(mockAvailableCourses);
        }
      } catch (error) {
        console.warn("Backend API unavailable, using mock data.", error);
        setAvailableCourses(mockAvailableCourses);
      } finally {
        setLoading(false);
      }
    };
    fetchCourses();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Courses</h1>
          <p className="text-gray-600 mt-1">Manage and track your enrolled courses.</p>
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

      {/* Empty State / Browse Prompt if no courses */}
      {isNewUser && (
        <div className="bg-white p-12 rounded-xl border border-gray-200 shadow-sm flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mb-6">
            <Compass size={40} />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">You haven't registered for any courses</h2>
          <p className="text-gray-500 max-w-md mb-8">
            Browse our catalog of AI-generated courses below to begin your learning journey.
          </p>
        </div>
      )}

      {/* Active Courses (only show if enrolled) */}
      {!isNewUser && (
        <div className="space-y-4">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Continue Learning</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {mockMyCourses.map(course => (
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
        <h3 className="text-xl font-bold text-gray-900 mb-6">Trending Courses</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {availableCourses.map(course => (
            <div key={course.id} className="group bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow flex flex-col">
              <div className="h-32 w-full overflow-hidden bg-gray-100">
                <img src={course.imageUrl} alt={course.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
              </div>
              <div className="p-5 flex flex-col flex-1">
                <span 
                  onClick={() => navigate(`/student/courses/category/${encodeURIComponent(course.category)}`)}
                  className="text-xs font-semibold text-blue-600 tracking-wider uppercase mb-2 cursor-pointer hover:underline"
                >
                  {course.category}
                </span>
                <h4 className="font-bold text-gray-900 mb-4 flex-1 cursor-pointer hover:text-blue-600 transition-colors">{course.title}</h4>
                <button 
                  onClick={async () => {
                    try {
                      const { api } = await import('../../services/api');
                      await api.enrollStudent(1, course.id);
                      alert("Successfully registered for course!");
                      setIsNewUser(false);
                    } catch (err) {
                      console.warn("Failed to register via API. Faking it for demo.", err);
                      alert("Successfully registered for course! (Mock)");
                      setIsNewUser(false);
                    }
                  }}
                  className="w-full py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:text-blue-600 hover:border-blue-300 transition-colors cursor-pointer"
                >
                  Register Course
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default StudentCourses;

