import React, { useState, useEffect } from 'react';
import { Settings, Plus, CheckCircle, GripVertical, Clock, Calendar, AlertCircle, X, Sun, Moon, ArrowLeft, ShieldCheck } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

const CourseBuilder = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [showTimetableModal, setShowTimetableModal] = useState(false);
  const [error, setError] = useState('');
  const [course, setCourse] = useState(null);
  const [isApproved, setIsApproved] = useState(false);

  useEffect(() => {
    // 1. Check if course is in approvedCourses
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    const pending = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    
    let foundCourse = approved.find(c => c.id.toString() === id?.toString());
    if (foundCourse) {
      setIsApproved(true);
    } else {
      foundCourse = pending.find(c => c.id.toString() === id?.toString());
      setIsApproved(false);
    }

    // Default template if creating a fresh course or if not found
    if (!foundCourse) {
      foundCourse = {
        id: id || Date.now(),
        title: 'Python Programming',
        description: 'Learn Python from fundamentals to advanced concepts.',
        category: 'Computer Science',
        modules: [
          {
            id: 1,
            title: 'Python Fundamentals',
            lessons: [
              'Introduction to Python',
              'Variables',
              'Data Types',
              'Operators'
            ]
          },
          {
            id: 2,
            title: 'Control Flow',
            lessons: [
              'Conditions',
              'Loops',
              'Functions'
            ]
          }
        ]
      };
    }

    // Ensure modules has structure
    if (!foundCourse.modules || foundCourse.modules.length === 0) {
      foundCourse.modules = [
        {
          id: 1,
          title: 'Module 1: Foundations',
          lessons: ['Introduction & Setup', 'Core Concepts', 'Syntactic Overview']
        },
        {
          id: 2,
          title: 'Module 2: Applied Techniques',
          lessons: ['Patterns & Practices', 'Debugging', 'Capstone Challenge']
        }
      ];
    }

    setCourse(foundCourse);
  }, [id]);

  if (!course) return null;

  const handleConfirmSubmission = (e) => {
    e.preventDefault();
    setError('');

    const form = e.target;
    const day = form.day.value;
    const lectureStart = form.lectureStart.value;
    const lectureEnd = form.lectureEnd.value;
    const practiceStart = form.practiceStart.value;
    const practiceEnd = form.practiceEnd.value;
    const room = form.room.value.trim() || 'Hall B / Code Lab 1';

    // Time validation
    if (!lectureStart || !lectureEnd || !practiceStart || !practiceEnd) {
      setError('Please specify both lecture and practice session hours.');
      return;
    }

    if (lectureStart >= lectureEnd) {
      setError('Lecture end time must be after start time.');
      return;
    }

    if (practiceStart >= practiceEnd) {
      setError('Practice session end time must be after start time.');
      return;
    }

    // Convert to minutes
    const [lStartH, lStartM] = lectureStart.split(':').map(Number);
    const [lEndH, lEndM] = lectureEnd.split(':').map(Number);
    const [pStartH, pStartM] = practiceStart.split(':').map(Number);

    const lEndMinutes = lEndH * 60 + lEndM;
    const pStartMinutes = pStartH * 60 + pStartM;

    // Rule: Lecture must be strictly before 6:00 PM (18:00 = 1080 min)
    if (lEndMinutes > 18 * 60) {
      setError('Policy Violation: Default lecture slots must be scheduled strictly BEFORE 6:00 PM (18:00).');
      return;
    }

    // Rule: Practice session must be strictly after 6:30 PM (18:30 = 1110 min)
    if (pStartMinutes < 18 * 60 + 30) {
      setError('Policy Violation: Default practice sessions must be scheduled strictly AFTER 6:30 PM (18:30).');
      return;
    }

    const teacherName = localStorage.getItem('userName') || 'Teacher';
    const teacherEmail = localStorage.getItem('userEmail') || 'teacher@lms.edu';
    
    const newRequest = {
      id: course.id || Date.now(),
      title: course.title,
      description: course.description,
      category: course.category || 'Computer Science',
      teacherName,
      teacherEmail,
      status: 'pending',
      createdAt: new Date().toISOString(),
      modules: course.modules,
      imageUrl: course.imageUrl || 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=500&q=80',
      defaultTimetable: {
        day,
        lectureStart,
        lectureEnd,
        practiceStart,
        practiceEnd,
        room
      }
    };

    const currentRequests = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    // Filter duplicates
    const filtered = currentRequests.filter(r => !(r.title === newRequest.title && r.teacherEmail === teacherEmail));
    filtered.push(newRequest);
    localStorage.setItem('pendingCourseRequests', JSON.stringify(filtered));

    setShowTimetableModal(false);
    alert('Course with default timetable schedule has been submitted to the Administrator for approval!');
    navigate('/teacher/courses');
  };

  return (
    <div className="max-w-4xl mx-auto pb-12">
      <button 
        onClick={() => navigate('/teacher/courses')}
        className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-blue-600 mb-6 transition-colors cursor-pointer"
      >
        <ArrowLeft size={16} /> Back to My Courses
      </button>

      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-blue-600">Course Builder & Curriculum</span>
            {isApproved ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
                <ShieldCheck size={12} /> Approved & Live in Catalog
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                Pending / Draft
              </span>
            )}
          </div>
          <h1 className="text-3xl font-bold text-gray-900">{course.title}</h1>
          <p className="text-gray-600 mt-2">{course.description}</p>
        </div>

        <div className="flex items-center gap-3">
          {isApproved ? (
            <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold">
              <CheckCircle size={16} className="text-emerald-600" /> Published by Academic Admin
            </div>
          ) : (
            <>
              <button 
                onClick={() => { alert('Draft saved locally.'); navigate('/teacher/courses'); }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50 cursor-pointer"
              >
                Save Draft
              </button>
              <button 
                onClick={() => setShowTimetableModal(true)}
                className="px-5 py-2 bg-blue-600 text-white rounded-md text-sm font-bold hover:bg-blue-700 shadow-sm cursor-pointer flex items-center gap-2"
              >
                <Clock size={16} /> Submit for Admin Approval
              </button>
            </>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {course.modules.map((module, mIndex) => (
          <div key={module.id || mIndex} className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <div className="bg-gray-50 border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Module {mIndex + 1}</span>
                <h3 className="text-lg font-bold text-gray-900">{module.title || module.name || `Module ${mIndex + 1}`}</h3>
              </div>
              <button className="text-gray-400 hover:text-gray-600">
                <Settings size={18} />
              </button>
            </div>
            
            <div className="p-2">
              {(module.lessons || ['Introduction', 'Core Architecture', 'Practice Assignment']).map((lesson, lIndex) => (
                <div key={lIndex} className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg group">
                  <GripVertical size={16} className="text-gray-300 cursor-grab" />
                  <CheckCircle size={16} className="text-emerald-500" />
                  <span className="text-sm font-medium text-gray-500 w-20">Lesson {lIndex + 1}</span>
                  <span className="text-sm text-gray-900 flex-1 font-medium">{lesson}</span>
                  <button className="text-gray-400 hover:text-blue-600 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                    Edit
                  </button>
                </div>
              ))}
            </div>
            
            <div className="px-6 py-3 border-t border-gray-100 bg-gray-50">
              <button className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800">
                <Plus size={16} /> Add Lesson
              </button>
            </div>
          </div>
        ))}

        {!isApproved && (
          <button className="w-full py-4 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 font-medium hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors flex items-center justify-center gap-2 cursor-pointer">
            <Plus size={20} /> Add Module
          </button>
        )}
      </div>

      {/* Default Timetable Specification Modal (Mandatory before Admin submission) */}
      {showTimetableModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <div>
                <h3 className="font-bold text-gray-900 flex items-center gap-2 text-base">
                  <Clock size={18} className="text-blue-600" />
                  Specify Default Course Timetable
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  Academic policy requires a proposed default lecture and lab schedule before administrator review.
                </p>
              </div>
              <button onClick={() => setShowTimetableModal(false)} className="text-gray-400 hover:text-gray-600 cursor-pointer">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleConfirmSubmission} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-start gap-2">
                  <AlertCircle size={16} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Teaching Day *</label>
                  <select
                    name="day"
                    defaultValue="Monday"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                  >
                    {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Room / Venue</label>
                  <input
                    name="room"
                    type="text"
                    defaultValue="Lecture Hall A / Code Lab"
                    placeholder="e.g., Room 302"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              {/* Lecture Timing Section */}
              <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900">
                  <Sun size={14} className="text-blue-600" />
                  <span>Default Regular Lecture Timing (Must be &lt; 6:00 PM)</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-gray-600 mb-0.5">Start Time</label>
                    <input
                      name="lectureStart"
                      type="time"
                      required
                      defaultValue="10:00"
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-gray-600 mb-0.5">End Time</label>
                    <input
                      name="lectureEnd"
                      type="time"
                      required
                      defaultValue="11:30"
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* Practice Session Timing Section */}
              <div className="p-3.5 bg-purple-50/70 border border-purple-200 rounded-xl space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-purple-900">
                  <Moon size={14} className="text-purple-600" />
                  <span>Default Practice / Lab Session (Must be &gt; 6:30 PM)</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-gray-600 mb-0.5">Start Time</label>
                    <input
                      name="practiceStart"
                      type="time"
                      required
                      defaultValue="19:00"
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-gray-600 mb-0.5">End Time</label>
                    <input
                      name="practiceEnd"
                      type="time"
                      required
                      defaultValue="20:30"
                      className="w-full px-3 py-1.5 bg-white border border-gray-300 rounded-lg text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowTimetableModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 shadow-sm cursor-pointer"
                >
                  Confirm & Submit to Admin
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default CourseBuilder;
