import React, { useState, useEffect } from 'react';
import { Users, Plus, Mail, BookOpen, Star, Trash2, CheckCircle, AlertCircle, X, ShieldCheck, BookMarked, UserCheck } from 'lucide-react';

const AdminFaculty = () => {
  const [faculty, setFaculty] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedFacultyForSubject, setSelectedFacultyForSubject] = useState(null);
  const [subjectAssignments, setSubjectAssignments] = useState({});
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const standardSubjects = [
    "Web Development",
    "Mathematics",
    "History",
    "Physics",
    "Computer Science",
    "Biology",
    "Chemistry",
    "Data Science",
    "Machine Learning",
    "Art History",
    "Literature",
    "Philosophy",
    "Economics",
    "Psychology",
    "Sociology",
    "Business",
    "Marketing",
    "Design",
    "Cybersecurity",
    "Networking",
    "Languages"
  ];

  // Default initial faculty
  const defaultFaculty = [
    {
      id: 1,
      name: 'Dr. Alan Turing',
      email: 'alan.turing@lms.edu',
      department: 'Computer Science & AI',
      subject: 'Web Development',
      style: 'Theoretical & Intensive',
      avatar: 'https://ui-avatars.com/api/?name=Alan+Turing&background=0D8ABC&color=fff',
      rating: 4.9,
      isDefault: true
    },
    {
      id: 2,
      name: 'Prof. Grace Hopper',
      email: 'grace.hopper@lms.edu',
      department: 'Software Engineering',
      subject: 'Computer Science',
      style: 'Practical & Project-Based',
      avatar: 'https://ui-avatars.com/api/?name=Grace+Hopper&background=10B981&color=fff',
      rating: 4.8,
      isDefault: true
    },
    {
      id: 3,
      name: 'Dr. Ada Lovelace',
      email: 'ada.lovelace@lms.edu',
      department: 'Mathematics & Algorithms',
      subject: 'Mathematics',
      style: 'Paced & Beginner Friendly',
      avatar: 'https://ui-avatars.com/api/?name=Ada+Lovelace&background=8B5CF6&color=fff',
      rating: 5.0,
      isDefault: true
    }
  ];

  const loadFaculty = () => {
    const custom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const assignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');
    setSubjectAssignments(assignments);

    // Merge subject assignment onto faculty objects
    const all = [...defaultFaculty, ...custom].map(f => ({
      ...f,
      subject: assignments[f.id] || f.subject || f.department || 'General Academics'
    }));

    setFaculty(all);
  };

  useEffect(() => {
    loadFaculty();
  }, []);

  const handleAddTeacherForSubject = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const form = e.target;
    const name = form.name.value.trim();
    const email = form.email.value.trim().toLowerCase();
    const subject = form.subject.value.trim();
    const style = form.style.value.trim();

    // Verification: Email must end in @lms.edu
    if (!email.endsWith('@lms.edu')) {
      setError('Teacher institutional email must end with @lms.edu');
      return;
    }

    // Check duplicate email
    if (faculty.some(f => f.email.toLowerCase() === email)) {
      setError('A teacher with this email already exists.');
      return;
    }

    const newTeacherId = Date.now();
    const newFacultyMember = {
      id: newTeacherId,
      name,
      email,
      department: subject,
      subject,
      style: style || 'Interactive & Engaging',
      avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=3B82F6&color=fff`,
      rating: 5.0,
      isDefault: false
    };

    // Save custom faculty
    const currentCustom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const updated = [...currentCustom, newFacultyMember];
    localStorage.setItem('customFacultyList', JSON.stringify(updated));

    // Save subject assignment
    const assignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');
    assignments[newTeacherId] = subject;
    localStorage.setItem('teacherSubjectAssignments', JSON.stringify(assignments));

    setSuccess(`Teacher "${name}" successfully appointed for the subject "${subject}"!`);
    loadFaculty();
    form.reset();
    setTimeout(() => {
      setShowAddModal(false);
      setSuccess('');
    }, 1200);
  };

  const handleAssignSubject = (e) => {
    e.preventDefault();
    if (!selectedFacultyForSubject) return;

    const subject = e.target.subject.value;
    const assignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');
    assignments[selectedFacultyForSubject.id] = subject;
    localStorage.setItem('teacherSubjectAssignments', JSON.stringify(assignments));

    // Also update customFacultyList if it's a custom teacher
    const currentCustom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const updatedCustom = currentCustom.map(f => f.id === selectedFacultyForSubject.id ? { ...f, subject } : f);
    localStorage.setItem('customFacultyList', JSON.stringify(updatedCustom));

    setSuccess(`Successfully allocated "${subject}" to ${selectedFacultyForSubject.name}!`);
    loadFaculty();
    setTimeout(() => {
      setShowAssignModal(false);
      setSelectedFacultyForSubject(null);
      setSuccess('');
    }, 1000);
  };

  const handleRemoveCustomFaculty = (id) => {
    if (!window.confirm('Are you sure you want to remove this faculty member?')) return;
    const currentCustom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const updated = currentCustom.filter(f => f.id !== id);
    localStorage.setItem('customFacultyList', JSON.stringify(updated));

    const assignments = JSON.parse(localStorage.getItem('teacherSubjectAssignments') || '{}');
    delete assignments[id];
    localStorage.setItem('teacherSubjectAssignments', JSON.stringify(assignments));

    loadFaculty();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Faculty & Subject Management</h1>
          <p className="text-gray-600 mt-1">Appoint instructors for subjects, allocate academic curriculum, and oversee faculty credentials.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setShowAddModal(true); setError(''); setSuccess(''); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
          >
            <Plus size={18} /> Add Teacher for Subject
          </button>
        </div>
      </div>

      {success && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-sm flex items-center gap-3">
          <CheckCircle size={20} className="text-emerald-600 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Faculty Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {faculty.map((member) => (
          <div key={member.id} className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between relative">
            <div>
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <img src={member.avatar} alt={member.name} className="w-14 h-14 rounded-full ring-2 ring-blue-50" />
                  <div>
                    <h3 className="font-bold text-gray-900 text-base">{member.name}</h3>
                    <span className="text-xs text-gray-400 font-mono block">{member.email}</span>
                  </div>
                </div>
                {!member.isDefault && (
                  <button
                    onClick={() => handleRemoveCustomFaculty(member.id)}
                    className="text-gray-400 hover:text-red-600 p-1 rounded transition-colors"
                    title="Remove Teacher"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>

              {/* Assigned Subject Badge */}
              <div className="mt-2 p-3 bg-blue-50/80 border border-blue-100 rounded-lg flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider block">Assigned Subject:</span>
                  <span className="text-sm font-bold text-gray-900">{member.subject}</span>
                </div>
                <button
                  onClick={() => { setSelectedFacultyForSubject(member); setShowAssignModal(true); setError(''); setSuccess(''); }}
                  className="text-xs font-semibold text-blue-700 hover:underline cursor-pointer"
                >
                  Change
                </button>
              </div>

              <div className="space-y-2 mt-4 pt-3 border-t border-gray-100">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Teaching Pedagogy:</span>
                  <span className="font-medium text-gray-700 bg-gray-100 px-2 py-0.5 rounded">{member.style}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Student Rating:</span>
                  <span className="font-semibold text-amber-600 flex items-center gap-1">
                    <Star size={12} className="fill-current" /> {member.rating} / 5.0
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
              <span>{member.isDefault ? 'Tenured Faculty' : 'Newly Appointed'}</span>
              <span className="text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle size={12} /> Active Instructor
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Modal 1: Add New Teacher for a Subject */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Users size={18} className="text-blue-600" />
                Appoint New Teacher for Subject
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddTeacherForSubject} className="p-6 space-y-4">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-start gap-2">
                  <AlertCircle size={16} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg text-xs flex items-start gap-2">
                  <CheckCircle size={16} className="shrink-0 mt-0.5" />
                  <span>{success}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Teacher Full Name *</label>
                <input
                  name="name"
                  type="text"
                  required
                  placeholder="e.g., Prof. Richard Feynman"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Institutional Email * <span className="text-gray-400 font-normal">(must end in @lms.edu)</span>
                </label>
                <input
                  name="email"
                  type="email"
                  required
                  placeholder="e.g., r.feynman@lms.edu"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Assigned Subject / Discipline *</label>
                <select
                  name="subject"
                  required
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 bg-white"
                >
                  {standardSubjects.map(sub => (
                    <option key={sub} value={sub}>{sub}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Teaching Pedagogy / Style</label>
                <select
                  name="style"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500 bg-white"
                >
                  <option value="Conceptual & Intuitive">Conceptual & Intuitive</option>
                  <option value="Theoretical & Rigorous">Theoretical & Rigorous</option>
                  <option value="Project-Based & Practical">Project-Based & Practical</option>
                  <option value="Paced & Beginner Friendly">Paced & Beginner Friendly</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm cursor-pointer"
                >
                  Appoint Teacher
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Change Subject for Teacher */}
      {showAssignModal && selectedFacultyForSubject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div className="flex justify-between items-center p-4 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 text-sm">Assign Subject to {selectedFacultyForSubject.name}</h3>
              <button onClick={() => setShowAssignModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleAssignSubject} className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Select Subject</label>
                <select
                  name="subject"
                  defaultValue={selectedFacultyForSubject.subject}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  {standardSubjects.map(sub => (
                    <option key={sub} value={sub}>{sub}</option>
                  ))}
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 shadow-sm"
                >
                  Save Assignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminFaculty;
