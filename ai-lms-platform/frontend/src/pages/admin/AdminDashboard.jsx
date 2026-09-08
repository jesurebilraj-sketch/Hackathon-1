import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, BookOpen, CheckSquare, Clock, ArrowUpRight, Plus, ShieldCheck, UserCheck, Calendar, Sun, Moon, BookMarked } from 'lucide-react';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [facultyList, setFacultyList] = useState([]);
  const [selectedTeacherId, setSelectedTeacherId] = useState(null);
  const [timetables, setTimetables] = useState([]);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [activeCoursesCount, setActiveCoursesCount] = useState(4);
  const [subjectAssignments, setSubjectAssignments] = useState({});

  useEffect(() => {
    // 1. Load Registered Faculty
    const defaultFaculty = [
      { id: 1, name: 'Dr. Alan Turing', email: 'alan.turing@lms.edu', department: 'Computer Science', subject: 'Web Development' },
      { id: 2, name: 'Prof. Grace Hopper', email: 'grace.hopper@lms.edu', department: 'Software Engineering', subject: 'Computer Science' },
      { id: 3, name: 'Dr. Ada Lovelace', email: 'ada.lovelace@lms.edu', department: 'Mathematics', subject: 'Mathematics' }
    ];
    const customFaculty = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const allFaculty = [...defaultFaculty, ...customFaculty];
    setFacultyList(allFaculty);
    if (allFaculty.length > 0) {
      setSelectedTeacherId(allFaculty[0].id);
    }

    // 2. Load Subject Assignments
    const assignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');
    setSubjectAssignments(assignments);

    // 3. Pending Course Requests from Teachers
    const requests = JSON.parse(localStorage.getItem('pendingCourseRequests') || '[]');
    setPendingRequests(requests.filter(r => r.status === 'pending'));

    // 4. Approved / Available Courses
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    setActiveCoursesCount(approved.length);

    // 5. Load Timetables
    const savedTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
    setTimetables(savedTimetables);
  }, []);

  const selectedTeacher = facultyList.find(f => f.id === selectedTeacherId) || facultyList[0];

  // Filter timetable strictly for the selected registered teacher
  const teacherTimetable = timetables.filter(t => {
    if (!selectedTeacher) return false;
    if (t.instructor === selectedTeacher.name) return true;
    if (t.teacherId && t.teacherId === selectedTeacher.id) return true;
    // Fallback matching by name snippet
    const lastName = selectedTeacher.name.split(' ').pop();
    return t.instructor && t.instructor.includes(lastName);
  });

  const stats = [
    { title: 'Registered Teachers', value: facultyList.length, icon: <Users size={22} />, color: 'bg-blue-500', link: '/admin/faculty' },
    { title: 'Active Courses', value: activeCoursesCount, icon: <BookOpen size={22} />, color: 'bg-emerald-500', link: '/admin/courses' },
    { title: 'Pending Approvals', value: pendingRequests.length, icon: <CheckSquare size={22} />, color: 'bg-amber-500', link: '/admin/courses' },
    { title: 'Subject Assignments', value: Object.keys(subjectAssignments).length + 3, icon: <BookMarked size={22} />, color: 'bg-indigo-500', link: '/admin/faculty' },
  ];

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 flex items-center gap-1">
              <ShieldCheck size={12} /> University Administrator Portal
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Administrator Console</h1>
          <p className="text-gray-600 mt-1">Supervise registered teachers, inspect their timetables, and allocate faculty to subjects.</p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/admin/faculty')}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer"
          >
            <Plus size={16} /> Add Teacher for Subject
          </button>
          <button 
            onClick={() => navigate('/admin/courses')}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors shadow-sm cursor-pointer"
          >
            <CheckSquare size={16} /> Course Approvals ({pendingRequests.length})
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {stats.map((stat, idx) => (
          <div 
            key={idx}
            onClick={() => navigate(stat.link)}
            className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-500">{stat.title}</span>
              <div className={`w-10 h-10 rounded-lg ${stat.color} text-white flex items-center justify-center`}>
                {stat.icon}
              </div>
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-3xl font-bold text-gray-900">{stat.value}</span>
              <span className="text-xs font-semibold text-blue-600 flex items-center gap-0.5 hover:underline">
                Manage <ArrowUpRight size={14} />
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Registered Teachers' Timetable Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <Clock className="text-blue-600" size={20} />
              Registered Teachers' Timetable
            </h2>
            <p className="text-sm text-gray-500">
              Select any registered teacher to inspect their official teaching hours (classes &lt; 6:00 PM and practice labs &gt; 6:30 PM).
            </p>
          </div>

          {/* Teacher Selector Dropdown */}
          <div className="flex items-center gap-3">
            <label className="text-xs font-semibold text-gray-600 shrink-0">Select Teacher:</label>
            <select
              value={selectedTeacherId || ''}
              onChange={(e) => setSelectedTeacherId(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white font-medium text-gray-900 focus:ring-blue-500 focus:border-blue-500 shadow-2xs cursor-pointer"
            >
              {facultyList.map(teacher => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.name} ({teacher.subject || teacher.department || 'Faculty'})
                </option>
              ))}
            </select>
            <button
              onClick={() => navigate('/admin/timetable')}
              className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-medium transition-colors"
            >
              Edit Slots
            </button>
          </div>
        </div>

        {/* Selected Teacher Profile Snapshot */}
        {selectedTeacher && (
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-blue-50/60 border border-blue-100 rounded-xl">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg shadow-sm">
                {selectedTeacher.name.charAt(0)}
              </div>
              <div>
                <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
                  {selectedTeacher.name}
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                    Registered Faculty
                  </span>
                </h3>
                <p className="text-xs text-gray-600">{selectedTeacher.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-6 text-xs text-gray-700">
              <div>
                <span className="text-gray-400 block">Assigned Subject:</span>
                <span className="font-bold text-blue-700">
                  {selectedTeacher.subject || subjectAssignments[selectedTeacher.id] || selectedTeacher.department || 'General Academics'}
                </span>
              </div>
              <div>
                <span className="text-gray-400 block">Total Weekly Slots:</span>
                <span className="font-bold text-gray-900">{teacherTimetable.length} sessions</span>
              </div>
            </div>
          </div>
        )}

        {/* Timetable Schedule Grid for Selected Teacher */}
        {teacherTimetable.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-xl bg-gray-50/50">
            <Clock size={32} className="mx-auto text-gray-400 mb-2" />
            <h4 className="text-sm font-bold text-gray-800">No Timetable Scheduled for this Teacher</h4>
            <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1 mb-4">
              Use the Timetable Manager to assign teaching slots (&lt; 6:00 PM) or evening practice sessions (&gt; 6:30 PM).
            </p>
            <button
              onClick={() => navigate('/admin/timetable')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors shadow-sm"
            >
              Add Schedule Slot for {selectedTeacher?.name}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {teacherTimetable.map((slot) => (
              <div 
                key={slot.id} 
                className={`p-4 rounded-xl border transition-all ${
                  slot.sessionType === 'class'
                    ? 'bg-blue-50/50 border-blue-200'
                    : 'bg-purple-50/50 border-purple-200'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase flex items-center gap-1 ${
                    slot.sessionType === 'class'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-purple-100 text-purple-800'
                  }`}>
                    {slot.sessionType === 'class' ? <Sun size={10} /> : <Moon size={10} />}
                    {slot.sessionType === 'class' ? 'Class (< 6:00 PM)' : 'Practice Lab (> 6:30 PM)'}
                  </span>
                  <span className="text-xs font-bold text-gray-700">{slot.day}</span>
                </div>

                <h4 className="font-bold text-gray-900 text-sm mb-1">{slot.courseTitle}</h4>

                <div className="space-y-1 text-xs text-gray-600 mt-3 pt-2 border-t border-gray-100">
                  <div className="flex items-center gap-1.5 font-semibold text-gray-900">
                    <Clock size={14} className={slot.sessionType === 'class' ? 'text-blue-600' : 'text-purple-600'} />
                    <span>{slot.startTime} – {slot.endTime}</span>
                  </div>
                  <div className="text-gray-500">
                    Venue: <span className="font-medium text-gray-700">{slot.room}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Course Approvals Quick List */}
      {pendingRequests.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-100">
            <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
              <CheckSquare className="text-amber-500" size={18} />
              Teacher Course Requests Awaiting Approval ({pendingRequests.length})
            </h3>
            <button
              onClick={() => navigate('/admin/courses')}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800"
            >
              Review All Requests &rarr;
            </button>
          </div>
          <div className="space-y-3">
            {pendingRequests.slice(0, 3).map((req) => (
              <div key={req.id} className="p-3.5 rounded-lg border border-gray-200 bg-gray-50/60 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-gray-900">{req.title}</h4>
                  <p className="text-xs text-gray-500">Submitted by: <span className="font-medium text-gray-700">{req.teacherName}</span> • {req.category}</p>
                </div>
                <button
                  onClick={() => navigate('/admin/courses')}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-xs font-medium hover:bg-blue-700 shadow-2xs"
                >
                  Approve Course
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
