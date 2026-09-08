import React, { useState, useEffect } from 'react';
import { BookOpen, CheckCircle, XCircle, Plus, CheckSquare, Clock, User, AlertCircle, Trash2, Eye } from 'lucide-react';

const AdminCourses = () => {
  const [activeTab, setActiveTab] = useState('requests'); // 'requests' | 'approved'
  const [pendingRequests, setPendingRequests] = useState([]);
  const [approvedCourses, setApprovedCourses] = useState([]);
  const [facultyList, setFacultyList] = useState([]);
  const [showDirectAddModal, setShowDirectAddModal] = useState(false);
  const [viewingCourse, setViewingCourse] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  const loadData = () => {
    // 1. Pending requests
    const allRequests = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    setPendingRequests(allRequests);

    // 2. Approved courses
    const liveApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    setApprovedCourses(liveApproved);

    // 3. Faculty
    const defaultFaculty = [
      { id: 1, name: 'Dr. Alan Turing', email: 'alan.turing@lms.edu' },
      { id: 2, name: 'Prof. Grace Hopper', email: 'grace.hopper@lms.edu' },
      { id: 3, name: 'Dr. Ada Lovelace', email: 'ada.lovelace@lms.edu' }
    ];
    const customFaculty = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    setFacultyList([...defaultFaculty, ...customFaculty]);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = (request) => {
    // 1. Mark request as approved
    const allRequests = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    const updatedRequests = allRequests.filter(r => r.id !== request.id);
    localStorage.setItem('pendingCourseRequests', JSON.stringify(updatedRequests));

    // 2. Add to approvedCourses (which are displayed in "Available Courses" for students)
    const currentApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    
    // Check if already in approved
    if (!currentApproved.some(c => c.id === request.id)) {
      currentApproved.push({
        id: request.id,
        title: request.title,
        description: request.description || 'Comprehensive curriculum approved by university administration.',
        category: request.category || 'Computer Science',
        teacher: request.teacherName || 'Faculty Member',
        teacherEmail: request.teacherEmail,
        imageUrl: request.imageUrl || 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=500&q=80',
        approvedAt: new Date().toISOString(),
        modules: request.modules || []
      });
      localStorage.setItem('approvedCourses', JSON.stringify(currentApproved));
    }

    // 3. Automatically register the teacher's specified default timetable slots!
    if (request.defaultTimetable) {
      const dt = request.defaultTimetable;
      const currentTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
      
      // Lecture slot (< 6 PM)
      currentTimetables.push({
        id: Date.now(),
        courseId: request.id,
        courseTitle: request.title,
        sessionType: 'class',
        day: dt.day || 'Monday',
        startTime: dt.lectureStart || '10:00',
        endTime: dt.lectureEnd || '11:30',
        room: dt.room || 'Lecture Hall A',
        instructor: request.teacherName || 'Faculty Member'
      });

      // Practice lab slot (> 6:30 PM)
      currentTimetables.push({
        id: Date.now() + 1,
        courseId: request.id,
        courseTitle: request.title,
        sessionType: 'practice',
        day: dt.day || 'Monday',
        startTime: dt.practiceStart || '19:00',
        endTime: dt.practiceEnd || '20:30',
        room: dt.room || 'Virtual Code Lab',
        instructor: request.teacherName || 'Faculty Member'
      });

      localStorage.setItem('courseTimetables', JSON.stringify(currentTimetables));
    }

    setSuccessMsg(`Course "${request.title}" and its default timetable have been approved! It is now live.`);
    loadData();
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  const handleReject = (requestId) => {
    if (!window.confirm('Reject this course request?')) return;
    const allRequests = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    const updatedRequests = allRequests.filter(r => r.id !== requestId);
    localStorage.setItem('pendingCourseRequests', JSON.stringify(updatedRequests));
    loadData();
  };

  const handleDeleteApprovedCourse = (courseId) => {
    if (!window.confirm('Remove this course from the public catalog?')) return;
    const currentApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    const updated = currentApproved.filter(c => c.id !== courseId);
    localStorage.setItem('approvedCourses', JSON.stringify(updated));
    loadData();
  };

  const handleDirectAddCourse = (e) => {
    e.preventDefault();
    const form = e.target;
    const title = form.title.value.trim();
    const category = form.category.value.trim();
    const teacherId = form.teacherId.value;
    const selectedTeacher = facultyList.find(f => f.id.toString() === teacherId) || facultyList[0];

    const newCourse = {
      id: Date.now(),
      title,
      description: form.description.value.trim() || 'Curriculum approved directly by academic administration.',
      category,
      teacher: selectedTeacher.name,
      teacherEmail: selectedTeacher.email,
      imageUrl: form.imageUrl.value.trim() || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=500&q=80',
      approvedAt: new Date().toISOString(),
      modules: [
        { name: 'Module 1: Introduction & Principles' },
        { name: 'Module 2: Core Architectures' },
        { name: 'Module 3: Practical Projects & Lab' },
      ]
    };

    const currentApproved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    currentApproved.push(newCourse);
    localStorage.setItem('approvedCourses', JSON.stringify(currentApproved));

    setSuccessMsg(`Course "${title}" added directly to Available Courses!`);
    loadData();
    setShowDirectAddModal(false);
    form.reset();
    setTimeout(() => setSuccessMsg(''), 3000);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Course Approvals & Curriculum Management</h1>
          <p className="text-gray-600 mt-1">Review faculty-submitted course proposals and publish approved courses to Available Courses.</p>
        </div>
        <button
          onClick={() => setShowDirectAddModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Plus size={18} /> Add Course Directly
        </button>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm flex items-center gap-3">
          <CheckCircle size={20} className="text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('requests')}
          className={`pb-3 px-4 font-semibold text-sm flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'requests'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <CheckSquare size={18} />
          Pending Teacher Requests
          {pendingRequests.length > 0 && (
            <span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-800 rounded-full font-bold">
              {pendingRequests.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('approved')}
          className={`pb-3 px-4 font-semibold text-sm flex items-center gap-2 border-b-2 transition-colors cursor-pointer ${
            activeTab === 'approved'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <BookOpen size={18} />
          Live Approved Catalog ({approvedCourses.length})
        </button>
      </div>

      {/* Tab 1: Pending Teacher Requests */}
      {activeTab === 'requests' && (
        <div className="space-y-4">
          {pendingRequests.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckSquare size={32} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">No Pending Course Requests</h3>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                When a teacher creates a course using the Course Builder and submits it for approval, it will appear here for administrative verification.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {pendingRequests.map((req) => (
                <div key={req.id} className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6 hover:border-blue-200 transition-colors">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-3">
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                        Awaiting Admin Approval
                      </span>
                      <span className="text-xs text-gray-400">Submitted: {new Date(req.createdAt || Date.now()).toLocaleDateString()}</span>
                    </div>
                    <h3 className="text-xl font-bold text-gray-900">{req.title}</h3>
                    <p className="text-sm text-gray-600 line-clamp-2">{req.description || 'No detailed syllabus description provided.'}</p>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 pt-1">
                      <span className="flex items-center gap-1 font-medium text-gray-700">
                        <User size={14} className="text-blue-600" /> Instructor: {req.teacherName} ({req.teacherEmail})
                      </span>
                      <span>•</span>
                      <span className="font-medium text-blue-600">{req.category}</span>
                      {req.modules && (
                        <>
                          <span>•</span>
                          <span>{req.modules.length} Modules structured</span>
                        </>
                      )}
                    </div>

                    {req.defaultTimetable && (
                      <div className="mt-2 p-2.5 bg-indigo-50 border border-indigo-100 rounded-lg text-xs flex flex-wrap items-center gap-3 text-indigo-900">
                        <span className="font-bold flex items-center gap-1 text-indigo-700">
                          <Calendar size={13} /> Proposed Default Timetable:
                        </span>
                        <span className="bg-white px-2 py-0.5 rounded border border-indigo-200 font-medium">
                          {req.defaultTimetable.day}
                        </span>
                        <span>
                          Lecture: <strong>{req.defaultTimetable.lectureStart} - {req.defaultTimetable.lectureEnd}</strong> (&lt; 6:00 PM)
                        </span>
                        <span>•</span>
                        <span>
                          Practice / Lab: <strong>{req.defaultTimetable.practiceStart} - {req.defaultTimetable.practiceEnd}</strong> (&gt; 6:30 PM)
                        </span>
                        {req.defaultTimetable.room && (
                          <>
                            <span>•</span>
                            <span className="text-gray-600">Room: {req.defaultTimetable.room}</span>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <button
                      onClick={() => setViewingCourse(req)}
                      className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <Eye size={16} /> Details
                    </button>
                    <button
                      onClick={() => handleReject(req.id)}
                      className="px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <XCircle size={16} /> Reject
                    </button>
                    <button
                      onClick={() => handleApprove(req)}
                      className="px-5 py-2 bg-emerald-600 text-white rounded-lg text-sm font-bold hover:bg-emerald-700 transition-colors shadow-sm flex items-center gap-1.5 cursor-pointer"
                    >
                      <CheckCircle size={16} /> Approve & Publish
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Live Approved Courses */}
      {activeTab === 'approved' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-xs text-blue-800">
            <strong>Active Catalog Notice:</strong> The courses below have been reviewed and approved by the Administrator. They are immediately live and available for students to browse and enroll under <strong>"Available Courses"</strong>.
          </div>

          {approvedCourses.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <div className="w-16 h-16 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mx-auto mb-4">
                <BookOpen size={32} />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">No Custom Courses Approved Yet</h3>
              <p className="text-sm text-gray-500 max-w-md mx-auto mb-6">
                Courses approved from teacher requests or added directly by the administrator will show up here and in the students' Trending Courses feed.
              </p>
              <button
                onClick={() => setShowDirectAddModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
              >
                Add Course to Catalog
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {approvedCourses.map((course) => (
                <div key={course.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                  <div>
                    <div className="h-40 w-full overflow-hidden relative">
                      <img src={course.imageUrl} alt={course.title} className="w-full h-full object-cover" />
                      <span className="absolute top-3 right-3 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-600 text-white shadow-sm flex items-center gap-1">
                        <CheckCircle size={12} /> Approved
                      </span>
                    </div>
                    <div className="p-5 space-y-2">
                      <span className="text-xs font-semibold text-blue-600 uppercase tracking-wider">{course.category}</span>
                      <h3 className="font-bold text-gray-900 text-lg">{course.title}</h3>
                      <p className="text-xs text-gray-500 line-clamp-2">{course.description}</p>
                      <div className="pt-2 text-xs text-gray-600 flex items-center gap-1.5">
                        <User size={14} className="text-gray-400" /> Instructor: <span className="font-medium">{course.teacher}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-5 pt-0 flex items-center justify-between border-t border-gray-100 mt-4">
                    <span className="text-xs text-emerald-600 font-semibold">Live in Catalog</span>
                    <button
                      onClick={() => handleDeleteApprovedCourse(course.id)}
                      className="text-gray-400 hover:text-red-600 p-1.5 rounded transition-colors"
                      title="Remove from Catalog"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Direct Add Course Modal */}
      {showDirectAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Plus size={18} className="text-blue-600" />
                Add Course Directly to Available Courses
              </h3>
              <button onClick={() => setShowDirectAddModal(false)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>

            <form onSubmit={handleDirectAddCourse} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Course Title *</label>
                <input
                  name="title"
                  type="text"
                  required
                  placeholder="e.g., Deep Learning with PyTorch"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Academic Field / Category *</label>
                  <select
                    name="category"
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="Web Development">Web Development</option>
                    <option value="Computer Science">Computer Science</option>
                    <option value="Machine Learning">Machine Learning</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Physics">Physics</option>
                    <option value="Data Science">Data Science</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Assigned Instructor *</label>
                  <select
                    name="teacherId"
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                  >
                    {facultyList.map(f => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Course Description</label>
                <textarea
                  name="description"
                  rows="3"
                  placeholder="Overview of course outcomes, prerequisites, and syllabus..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
                ></textarea>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Image URL (Optional)</label>
                <input
                  name="imageUrl"
                  type="url"
                  placeholder="https://images.unsplash.com/..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowDirectAddModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm"
                >
                  Approve & Publish to Catalog
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Course Details Modal */}
      {viewingCourse && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900">Syllabus Proposal Details</h3>
              <button onClick={() => setViewingCourse(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              <div>
                <h2 className="text-xl font-bold text-gray-900">{viewingCourse.title}</h2>
                <p className="text-xs text-blue-600 font-medium">{viewingCourse.category} • Instructor: {viewingCourse.teacherName}</p>
              </div>
              <p className="text-sm text-gray-600">{viewingCourse.description}</p>

              {viewingCourse.defaultTimetable && (
                <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-lg text-xs space-y-1">
                  <h4 className="font-bold text-indigo-900 flex items-center gap-1.5">
                    <Calendar size={14} /> Teacher Proposed Timetable:
                  </h4>
                  <p className="text-gray-700"><strong>Day:</strong> {viewingCourse.defaultTimetable.day}</p>
                  <p className="text-gray-700"><strong>Regular Lecture:</strong> {viewingCourse.defaultTimetable.lectureStart} - {viewingCourse.defaultTimetable.lectureEnd} (Before 6:00 PM)</p>
                  <p className="text-gray-700"><strong>Practice Session:</strong> {viewingCourse.defaultTimetable.practiceStart} - {viewingCourse.defaultTimetable.practiceEnd} (After 6:30 PM)</p>
                  {viewingCourse.defaultTimetable.room && (
                    <p className="text-gray-700"><strong>Room / Hall:</strong> {viewingCourse.defaultTimetable.room}</p>
                  )}
                </div>
              )}

              {viewingCourse.modules && viewingCourse.modules.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">Modules & Curriculum:</h4>
                  <div className="space-y-2">
                    {viewingCourse.modules.map((m, idx) => (
                      <div key={idx} className="p-2.5 rounded bg-gray-50 border border-gray-200 text-xs">
                        <span className="font-bold text-gray-900">{m.title || m.name || `Module ${idx + 1}`}</span>
                        {m.lessons && (
                          <p className="text-gray-500 mt-1">{m.lessons.join(' • ')}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
              <button
                onClick={() => {
                  handleApprove(viewingCourse);
                  setViewingCourse(null);
                }}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-bold hover:bg-emerald-700"
              >
                Approve Course Now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminCourses;

