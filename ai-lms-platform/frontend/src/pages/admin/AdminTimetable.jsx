import React, { useState, useEffect } from 'react';
import { Clock, Calendar, Plus, AlertCircle, CheckCircle, Trash2, BookOpen, ShieldCheck, Sun, Moon } from 'lucide-react';

const AdminTimetable = () => {
  const [timetables, setTimetables] = useState([]);
  const [availableCourses, setAvailableCourses] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Initial seed timetables adhering strictly to the time rules
  const defaultTimetables = [
    {
      id: 1,
      courseId: 101,
      courseTitle: 'Advanced React Patterns',
      sessionType: 'class', // regular lecture
      day: 'Monday',
      startTime: '10:00',
      endTime: '11:30',
      room: 'Lecture Hall 2',
      instructor: 'Dr. Alan Turing'
    },
    {
      id: 2,
      courseId: 101,
      courseTitle: 'Advanced React Patterns',
      sessionType: 'practice', // practice session
      day: 'Monday',
      startTime: '19:00',
      endTime: '20:30',
      room: 'Virtual Code Lab B',
      instructor: 'Dr. Alan Turing'
    },
    {
      id: 3,
      courseId: 102,
      courseTitle: 'Calculus I',
      sessionType: 'class',
      day: 'Wednesday',
      startTime: '14:00',
      endTime: '15:30',
      room: 'Math Annex 104',
      instructor: 'Dr. Ada Lovelace'
    },
    {
      id: 4,
      courseId: 102,
      courseTitle: 'Calculus I',
      sessionType: 'practice',
      day: 'Wednesday',
      startTime: '18:45',
      endTime: '20:15',
      room: 'Problem Solving Lab',
      instructor: 'Dr. Ada Lovelace'
    }
  ];

  const loadData = () => {
    // 1. Load Courses
    const defaultCourses = [
      { id: 101, title: 'Advanced React Patterns' },
      { id: 102, title: 'Calculus I' },
      { id: 103, title: 'World History: 20th Century' },
      { id: 104, title: 'Physics for Engineers' }
    ];
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    setAvailableCourses([...defaultCourses, ...approved]);

    // 2. Load Timetable
    const saved = localStorage.getItem('courseTimetables');
    if (!saved) {
      localStorage.setItem('courseTimetables', JSON.stringify(defaultTimetables));
      setTimetables(defaultTimetables);
    } else {
      setTimetables(JSON.parse(saved));
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddSchedule = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const form = e.target;
    const courseId = form.courseId.value;
    const selectedCourse = availableCourses.find(c => c.id.toString() === courseId);
    const sessionType = form.sessionType.value; // 'class' | 'practice'
    const day = form.day.value;
    const startTime = form.startTime.value; // "HH:MM"
    const endTime = form.endTime.value;     // "HH:MM"
    const room = form.room.value.trim() || (sessionType === 'class' ? 'Lecture Hall A' : 'Hands-On Lab 1');

    if (!startTime || !endTime) {
      setError('Please select valid start and end times.');
      return;
    }

    if (startTime >= endTime) {
      setError('End time must be after start time.');
      return;
    }

    // Convert "HH:MM" to minutes for strict comparison
    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);
    const startMinutes = startH * 60 + startM;
    const endMinutes = endH * 60 + endM;

    // Constraint 1: Course class / lecture timetable must be before 6:00 PM (18:00 = 1080 min)
    const sixPM = 18 * 60; // 1080 minutes
    if (sessionType === 'class') {
      if (endMinutes > sixPM || startMinutes >= sixPM) {
        setError('Time Policy Violation: Regular course lectures must be scheduled strictly BEFORE 6:00 PM (18:00).');
        return;
      }
    }

    // Constraint 2: Practice sessions must be scheduled after 6:30 PM (18:30 = 1110 min)
    const sixThirtyPM = 18 * 60 + 30; // 1110 minutes
    if (sessionType === 'practice') {
      if (startMinutes < sixThirtyPM) {
        setError('Time Policy Violation: Practice / Lab sessions must be scheduled strictly AFTER 6:30 PM (18:30).');
        return;
      }
    }

    const newEntry = {
      id: Date.now(),
      courseId: selectedCourse.id,
      courseTitle: selectedCourse.title,
      sessionType,
      day,
      startTime,
      endTime,
      room,
      instructor: selectedCourse.teacher || 'Assigned Faculty'
    };

    const updated = [...timetables, newEntry];
    setTimetables(updated);
    localStorage.setItem('courseTimetables', JSON.stringify(updated));

    setSuccess(`Successfully scheduled ${sessionType === 'class' ? 'Class' : 'Practice Session'} for "${selectedCourse.title}"!`);
    form.reset();
    setTimeout(() => {
      setShowAddModal(false);
      setSuccess('');
    }, 1200);
  };

  const handleDeleteEntry = (id) => {
    const updated = timetables.filter(t => t.id !== id);
    setTimetables(updated);
    localStorage.setItem('courseTimetables', JSON.stringify(updated));
  };

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Institutional Timetable & Scheduling</h1>
          <p className="text-gray-600 mt-1">Configure class lecture schedules and evening practice sessions with institutional constraints.</p>
        </div>
        <button
          onClick={() => { setShowAddModal(true); setError(''); setSuccess(''); }}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Plus size={18} /> Schedule Course Slot
        </button>
      </div>

      {/* Constraints Notice Banner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-900">
          <Sun className="text-blue-600 shrink-0 mt-0.5" size={18} />
          <div>
            <span className="font-bold block text-sm mb-0.5">Regular Course Classes (Daytime)</span>
            Must be scheduled <strong>strictly before 6:00 PM</strong> (08:00 AM – 06:00 PM). Lectures after 6 PM are not permitted.
          </div>
        </div>

        <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-start gap-3 text-xs text-purple-900">
          <Moon className="text-purple-600 shrink-0 mt-0.5" size={18} />
          <div>
            <span className="font-bold block text-sm mb-0.5">Practice Sessions & Labs (Evening)</span>
            Must be scheduled <strong>strictly after 6:30 PM</strong> (06:30 PM – 10:30 PM) for student hands-on exercises and coding labs.
          </div>
        </div>
      </div>

      {/* Timetable by Day */}
      <div className="space-y-6">
        {daysOfWeek.map((day) => {
          const daySessions = timetables
            .filter(t => t.day === day)
            .sort((a, b) => a.startTime.localeCompare(b.startTime));

          return (
            <div key={day} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="bg-gray-50/80 px-6 py-3.5 border-b border-gray-200 flex items-center justify-between">
                <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
                  <Calendar size={18} className="text-blue-600" />
                  {day}
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-gray-200 text-gray-700">
                  {daySessions.length} {daySessions.length === 1 ? 'Slot' : 'Slots'} Scheduled
                </span>
              </div>

              <div className="p-6">
                {daySessions.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No classes or practice sessions scheduled for {day}.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {daySessions.map((session) => (
                      <div 
                        key={session.id} 
                        className={`p-4 rounded-xl border transition-all relative ${
                          session.sessionType === 'class'
                            ? 'bg-blue-50/40 border-blue-200 hover:border-blue-400'
                            : 'bg-purple-50/40 border-purple-200 hover:border-purple-400'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md uppercase flex items-center gap-1 ${
                            session.sessionType === 'class'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-purple-100 text-purple-800'
                          }`}>
                            {session.sessionType === 'class' ? <Sun size={12} /> : <Moon size={12} />}
                            {session.sessionType === 'class' ? 'Lecture (< 6:00 PM)' : 'Practice (> 6:30 PM)'}
                          </span>
                          <button
                            onClick={() => handleDeleteEntry(session.id)}
                            className="text-gray-400 hover:text-red-600 p-1 transition-colors cursor-pointer"
                            title="Delete slot"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        <h4 className="font-bold text-gray-900 text-sm mb-1">{session.courseTitle}</h4>

                        <div className="space-y-1 text-xs text-gray-600 mt-2 pt-2 border-t border-gray-100">
                          <div className="flex items-center gap-1.5 font-semibold text-gray-800">
                            <Clock size={14} className={session.sessionType === 'class' ? 'text-blue-600' : 'text-purple-600'} />
                            <span>{session.startTime} – {session.endTime}</span>
                          </div>
                          <div className="text-gray-500">
                            Location: <span className="font-medium text-gray-700">{session.room}</span>
                          </div>
                          {session.instructor && (
                            <div className="text-gray-500">
                              Instructor: <span className="font-medium text-gray-700">{session.instructor}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Schedule Course Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Clock size={18} className="text-blue-600" />
                Schedule Course Timetable Slot
              </h3>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>

            <form onSubmit={handleAddSchedule} className="p-6 space-y-4">
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
                <label className="block text-xs font-semibold text-gray-700 mb-1">Select Course *</label>
                <select
                  name="courseId"
                  required
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                >
                  {availableCourses.map(c => (
                    <option key={c.id} value={c.id}>{c.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Session Type *</label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-blue-50/50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50">
                    <input type="radio" name="sessionType" value="class" defaultChecked className="text-blue-600" />
                    <div>
                      <span className="text-xs font-bold text-gray-900 block">Regular Class</span>
                      <span className="text-[10px] text-gray-500">Must be before 6:00 PM</span>
                    </div>
                  </label>

                  <label className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-purple-50/50 has-[:checked]:border-purple-500 has-[:checked]:bg-purple-50">
                    <input type="radio" name="sessionType" value="practice" className="text-purple-600" />
                    <div>
                      <span className="text-xs font-bold text-gray-900 block">Practice / Lab</span>
                      <span className="text-[10px] text-gray-500">Must be after 6:30 PM</span>
                    </div>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Day of the Week *</label>
                  <select
                    name="day"
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                  >
                    {daysOfWeek.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Room / Venue</label>
                  <input
                    name="room"
                    type="text"
                    placeholder="e.g., Room 302 / Lab A"
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Start Time *</label>
                  <input
                    name="startTime"
                    type="time"
                    required
                    defaultValue="10:00"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">End Time *</label>
                  <input
                    name="endTime"
                    type="time"
                    required
                    defaultValue="11:30"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-[11px] text-gray-500 space-y-1">
                <p>• <strong>Classes</strong>: 08:00 AM – 06:00 PM (18:00)</p>
                <p>• <strong>Practice Sessions</strong>: 06:30 PM (18:30) – 10:30 PM (22:30)</p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 shadow-sm"
                >
                  Confirm & Save Slot
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminTimetable;
