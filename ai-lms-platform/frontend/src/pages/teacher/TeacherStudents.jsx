import React, { useState } from 'react';
import { Search, Filter, MessageSquare, Eye, X, Send, User, ChevronRight, CheckCircle, Clock } from 'lucide-react';

const TeacherStudents = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [courseFilter, setCourseFilter] = useState('All');
  
  // Modals state
  const [messagingStudent, setMessagingStudent] = useState(null);
  const [messageText, setMessageText] = useState('');
  
  const [viewingStudent, setViewingStudent] = useState(null);

  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);

  React.useEffect(() => {
    const fetchStudents = async () => {
      setLoading(true);
      const teacherId = parseInt(localStorage.getItem('teacherId') || '1');
      let apiStudents = [];
      try {
        const { api } = await import('../../services/api');
        const data = await api.getTeacherStudents(teacherId);
        if (data && data.students) {
          apiStudents = data.students;
        }
      } catch (error) {
        console.warn("Failed to fetch API students. Using local mock state.", error);
      } finally {
        // Fallback check: If the API failed or returned empty, we could build a list from mockEnrollments,
        // but since we only want ACTUAL students who enroll in the portal, we should prioritize what we have.
        // Wait, local storage mockEnrollments is isolated per user.
        // The only way to see true enrollments across browsers is via the backend API.
        // If the backend fails, we have no global list.
        setStudents(apiStudents);
        setLoading(false);
      }
    };
    fetchStudents();
  }, []);

  const uniqueCourses = ['All', ...new Set(students.map(s => s.course))];

  const filteredStudents = students.filter(student => {
    const matchesSearch = student.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCourse = courseFilter === 'All' || student.course === courseFilter;
    return matchesSearch && matchesCourse;
  });

  const handleSendMessage = (e) => {
    e.preventDefault();
    // TODO: Wire to backend API later
    console.log(`Sending message to ${messagingStudent.name}: ${messageText}`);
    alert(`Message sent to ${messagingStudent.name}!`);
    setMessagingStudent(null);
    setMessageText('');
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Student Management</h1>
          <p className="text-gray-600 mt-1">Track progress, review grades, and communicate with your students.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-gray-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            placeholder="Search students by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="relative min-w-[200px]">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Filter className="h-5 w-5 text-gray-400" />
          </div>
          <select
            className="block w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 sm:text-sm appearance-none cursor-pointer"
            value={courseFilter}
            onChange={(e) => setCourseFilter(e.target.value)}
          >
            {uniqueCourses.map(course => (
              <option key={course} value={course}>{course}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Student Name</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Enrolled Course</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Progress</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Active</th>
                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredStudents.length > 0 ? (
                filteredStudents.map((student) => (
                  <tr key={student.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold">
                          {student.name.charAt(0)}
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{student.name}</div>
                          <div className="text-sm text-gray-500">{student.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 max-w-[200px] truncate" title={student.course}>{student.course}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-gray-700 w-8">{student.progress}%</span>
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${student.progress === 100 ? 'bg-emerald-500' : 'bg-blue-600'}`} 
                            style={{ width: `${student.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {student.lastActive}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-3">
                        <button 
                          onClick={() => setMessagingStudent(student)}
                          className="text-gray-400 hover:text-blue-600 transition-colors"
                          title="Message Student"
                        >
                          <MessageSquare size={18} />
                        </button>
                        <button 
                          onClick={() => setViewingStudent(student)}
                          className="text-gray-400 hover:text-blue-600 transition-colors"
                          title="View Details"
                        >
                          <Eye size={18} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                    No students found matching your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Message Modal */}
      {messagingStudent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-4 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <MessageSquare size={18} className="text-blue-600" />
                Message {messagingStudent.name}
              </h3>
              <button onClick={() => setMessagingStudent(null)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSendMessage} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Message Body</label>
                <textarea 
                  rows="5"
                  required
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 text-sm resize-none"
                  placeholder={`Type your message to ${messagingStudent.name} here...`}
                ></textarea>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button 
                  type="button" 
                  onClick={() => setMessagingStudent(null)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                >
                  <Send size={16} /> Send Message
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Details Side Drawer */}
      {viewingStudent && (
        <>
          <div className="fixed inset-0 bg-black/30 z-40 backdrop-blur-sm" onClick={() => setViewingStudent(null)}></div>
          <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl z-50 overflow-y-auto transform transition-transform duration-300 flex flex-col">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h2 className="text-xl font-bold text-gray-900">Student Profile</h2>
              <button onClick={() => setViewingStudent(null)} className="text-gray-400 hover:text-gray-600 rounded-full p-1 hover:bg-gray-100 transition-colors">
                <X size={24} />
              </button>
            </div>
            
            <div className="p-6 flex-1">
              <div className="flex items-center gap-4 mb-8">
                <div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-2xl">
                  {viewingStudent.name.charAt(0)}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">{viewingStudent.name}</h3>
                  <p className="text-gray-500">{viewingStudent.email}</p>
                </div>
              </div>

              <div className="mb-8">
                <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">Course Overview</h4>
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <p className="font-medium text-blue-600 mb-2">{viewingStudent.course}</p>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-600">Total Progress</span>
                    <span className="text-sm font-bold text-gray-900">{viewingStudent.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
                    <div className={`h-2 rounded-full ${viewingStudent.progress === 100 ? 'bg-emerald-500' : 'bg-blue-600'}`} style={{ width: `${viewingStudent.progress}%` }}></div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <Clock size={14} /> Last active: {viewingStudent.lastActive}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">Module Grades</h4>
                <div className="space-y-3">
                  {viewingStudent.modules.map((mod, idx) => (
                    <div key={idx} className="border border-gray-100 rounded-lg p-3 hover:border-blue-200 transition-colors">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-gray-900 truncate pr-4">{mod.name}</span>
                        <span className={`text-xs font-bold px-2 py-1 rounded-md ${
                          mod.grade === 'A' ? 'bg-emerald-100 text-emerald-700' :
                          mod.grade === 'B' || mod.grade === 'B+' ? 'bg-blue-100 text-blue-700' :
                          mod.grade === 'Pending' ? 'bg-gray-100 text-gray-600' :
                          'bg-orange-100 text-orange-700'
                        }`}>
                          {mod.grade}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                          <div 
                            className={`h-1.5 rounded-full ${mod.score >= 90 ? 'bg-emerald-500' : mod.score === 0 ? 'bg-transparent' : 'bg-blue-500'}`} 
                            style={{ width: `${mod.score}%` }}
                          ></div>
                        </div>
                        <span className="text-xs font-medium text-gray-500 w-8 text-right">{mod.score}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>
        </>
      )}

    </div>
  );
};

export default TeacherStudents;

