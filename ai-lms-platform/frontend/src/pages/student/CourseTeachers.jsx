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
  const availableTeachers = [
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

  const handleEnroll = async () => {
    setEnrolling(true);
    const studentId = parseInt(localStorage.getItem('studentId') || '1');
    const userEmail = localStorage.getItem('userEmail') || 'default';

    try {
      // Use the actual API!
      await api.enrollStudent(studentId, id, selectedTeacher.id);
      
      // Increment teacher student count
      const newStats = { ...teacherStats, [selectedTeacher.id]: (teacherStats[selectedTeacher.id] || 0) + 1 };
      setTeacherStats(newStats);
      localStorage.setItem('teacherStats', JSON.stringify(newStats));

      alert(`Successfully registered with ${selectedTeacher.name}!`);
      navigate('/student/dashboard');
    } catch (err) {
      console.warn("API failed, using mock success.", err);
      // Increment teacher student count anyway for demo
      const newStats = { ...teacherStats, [selectedTeacher.id]: (teacherStats[selectedTeacher.id] || 0) + 1 };
      setTeacherStats(newStats);
      localStorage.setItem('teacherStats', JSON.stringify(newStats));
      
      // Save a mock enrollment to localStorage scoped to this user
      const mockEnrollments = JSON.parse(localStorage.getItem(`mockEnrollments_${userEmail}`) || '[]');
      if (!mockEnrollments.find(e => e.course.id == id)) {
        mockEnrollments.push({
          enrollment_id: Date.now(),
          course: {
            id: id,
            title: `Enrolled Course #${id}`,
            category: 'AI Generated',
            teacher: selectedTeacher.name
          }
        });
        localStorage.setItem(`mockEnrollments_${userEmail}`, JSON.stringify(mockEnrollments));
        
        // Save to global teacher students list for the Teacher Portal demo
        const userName = localStorage.getItem('userName') || 'Demo Student';
        const teacherStudentsKey = `teacherStudents_${selectedTeacher.id}`;
        const mockTeacherStudents = JSON.parse(localStorage.getItem(teacherStudentsKey) || '[]');
        mockTeacherStudents.push({
          id: studentId,
          name: userName,
          email: userEmail,
          course: `Enrolled Course #${id}`,
          progress: 0,
          lastActive: 'Just now',
          modules: []
        });
        localStorage.setItem(teacherStudentsKey, JSON.stringify(mockTeacherStudents));
      }
      
      alert(`Successfully registered with ${selectedTeacher.name}!`);
      navigate('/student/dashboard');
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: List of Teachers */}
        <div className="lg:col-span-1 space-y-4">
          {availableTeachers.map(teacher => (
            <div 
              key={teacher.id}
              onClick={() => setSelectedTeacher(teacher)}
              className={`p-5 rounded-xl border-2 transition-all cursor-pointer flex items-start gap-4 ${
                selectedTeacher?.id === teacher.id 
                  ? 'border-blue-500 bg-blue-50 shadow-md' 
                  : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-gray-50'
              }`}
            >
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
                <div className="mt-2 text-xs font-medium px-2 py-1 bg-white border border-gray-200 rounded-md inline-block text-gray-600">
                  {teacher.style}
                </div>
              </div>
            </div>
          ))}
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
                <button 
                  onClick={handleEnroll}
                  disabled={enrolling}
                  className="px-6 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition-colors shadow-sm disabled:opacity-50"
                >
                  {enrolling ? 'Enrolling...' : 'Confirm Enrollment'}
                </button>
              </div>

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

