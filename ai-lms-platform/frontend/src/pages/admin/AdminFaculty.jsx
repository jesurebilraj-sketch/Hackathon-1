import React, { useState, useEffect } from 'react';
import { Users, Plus, Mail, BookOpen, Star, Trash2, CheckCircle, AlertCircle, X, ShieldCheck } from 'lucide-react';

const AdminFaculty = () => {
  const [faculty, setFaculty] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Default initial faculty
  const defaultFaculty = [
    {
      id: 1,
      name: 'Dr. Alan Turing',
      email: 'alan.turing@lms.edu',
      department: 'Computer Science & AI',
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
      style: 'Paced & Beginner Friendly',
      avatar: 'https://ui-avatars.com/api/?name=Ada+Lovelace&background=8B5CF6&color=fff',
      rating: 5.0,
      isDefault: true
    }
  ];

  const loadFaculty = () => {
    const custom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    setFaculty([...defaultFaculty, ...custom]);
  };

  useEffect(() => {
    loadFaculty();
  }, []);

  const handleAddFaculty = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const form = e.target;
    const name = form.name.value.trim();
    const email = form.email.value.trim().toLowerCase();
    const department = form.department.value.trim();
    const style = form.style.value.trim();

    // Verification: Email must end in @lms.edu
    if (!email.endsWith('@lms.edu')) {
      setError('Faculty institutional email must end with @lms.edu');
      return;
    }

    // Check duplicate email
    if (faculty.some(f => f.email.toLowerCase() === email)) {
      setError('A faculty member with this email already exists.');
      return;
    }

    const newFacultyMember = {
      id: Date.now(),
      name,
      email,
      department,
      style: style || 'Interactive & Engaging',
      avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=3B82F6&color=fff`,
      rating: 5.0,
      isDefault: false
    };

    const currentCustom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const updated = [...currentCustom, newFacultyMember];
    localStorage.setItem('customFacultyList', JSON.stringify(updated));

    setSuccess(`Faculty member "${name}" successfully registered! They can now log in and be assigned to courses.`);
    loadFaculty();
    form.reset();
    setTimeout(() => {
      setShowModal(false);
      setSuccess('');
    }, 1200);
  };

  const handleRemoveCustomFaculty = (id) => {
    if (!window.confirm('Are you sure you want to remove this faculty member?')) return;
    const currentCustom = JSON.parse(localStorage.getItem('customFacultyList') || '[]');
    const updated = currentCustom.filter(f => f.id !== id);
    localStorage.setItem('customFacultyList', JSON.stringify(updated));
    loadFaculty();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Faculty Management</h1>
          <p className="text-gray-600 mt-1">Appoint instructors, manage academic staff profiles, and oversee faculty credentials.</p>
        </div>
        <button
          onClick={() => { setShowModal(true); setError(''); setSuccess(''); }}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Plus size={18} /> Add New Faculty
        </button>
      </div>

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
                    <p className="text-xs text-blue-600 font-medium">{member.department}</p>
                    <span className="text-xs text-gray-400 font-mono">{member.email}</span>
                  </div>
                </div>
                {!member.isDefault && (
                  <button
                    onClick={() => handleRemoveCustomFaculty(member.id)}
                    className="text-gray-400 hover:text-red-600 p-1 rounded transition-colors"
                    title="Remove Faculty"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>

              <div className="space-y-2 mt-4 pt-4 border-t border-gray-100">
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
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">Status:</span>
                  <span className="font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded flex items-center gap-1">
                    <CheckCircle size={10} /> Active Faculty
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-400">
              <span>{member.isDefault ? 'Tenured Faculty' : 'Newly Appointed'}</span>
              <span className="text-blue-600 font-medium">Eligible for Courses</span>
            </div>
          </div>
        ))}
      </div>

      {/* Add Faculty Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Users size={18} className="text-blue-600" />
                Add New Faculty Member
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleAddFaculty} className="p-6 space-y-4">
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
                <label className="block text-xs font-semibold text-gray-700 mb-1">Full Name *</label>
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
                <label className="block text-xs font-semibold text-gray-700 mb-1">Department / Subject Area *</label>
                <input
                  name="department"
                  type="text"
                  required
                  placeholder="e.g., Quantum Physics & Mechanics"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Teaching Style / Pedagogy</label>
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
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm"
                >
                  Register Faculty
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
