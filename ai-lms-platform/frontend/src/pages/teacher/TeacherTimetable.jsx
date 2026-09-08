import React, { useState, useEffect } from 'react';
import { Clock, Calendar, Plus, Edit2, Trash2, CheckCircle, AlertCircle, Sun, Moon, BookOpen, X, Sparkles, Sliders } from 'lucide-react';

const TeacherTimetable = () => {
  const [timetables, setTimetables] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingSlot, setEditingSlot] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const teacherName = localStorage.getItem('userName') || 'Teacher';
  const teacherId = localStorage.getItem('teacherId') || '1';

  // Standard days of the academic week
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  const loadData = () => {
    // 1. Load ONLY courses that have been approved by the Administrator
    const approved = JSON.parse(localStorage.getItem('approvedCourses') || '[]');
    
    // Filter courses handled by this teacher
    const lastName = teacherName.split(' ').pop();
    const handledApproved = approved.filter(c => {
      if (c.teacherEmail && c.teacherEmail.toLowerCase() === (localStorage.getItem('userEmail') || '').toLowerCase()) return true;
      if (c.instructor && (c.instructor === teacherName || c.instructor.includes(lastName))) return true;
      if (c.teacher && (c.teacher === teacherName || c.teacher.includes(lastName))) return true;
      return false;
    });

    setMyCourses(handledApproved);

    // 2. Load all timetables and strictly retain only slots whose course is approved by the administrator
    const allTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
    const approvedOnlyTimetables = allTimetables.filter(slot => 
      approved.some(ac => ac.id === slot.courseId || ac.title?.toLowerCase() === slot.courseTitle?.toLowerCase())
    );
    setTimetables(approvedOnlyTimetables);
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filter slots strictly for this teacher from the approved courses
  const mySlots = timetables.filter(slot => {
    if (slot.instructor === teacherName) return true;
    if (slot.teacherId && slot.teacherId.toString() === teacherId.toString()) return true;
    // Name fallback snippet
    const lastName = teacherName.split(' ').pop();
    return slot.instructor && slot.instructor.includes(lastName);
  });

  const handleOpenModal = (slot = null) => {
    setEditingSlot(slot);
    setError('');
    setSuccess('');
    setShowModal(true);
  };

  const handleSaveSlot = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const form = e.target;
    const courseTitle = form.courseTitle.value;
    const sessionType = form.sessionType.value; // 'class' | 'practice'
    const day = form.day.value;
    const startTime = form.startTime.value;
    const endTime = form.endTime.value;
    const room = form.room.value.trim() || (sessionType === 'class' ? 'Lecture Hall 2' : 'Virtual Code Lab');

    if (!startTime || !endTime) {
      setError('Please select valid start and end times.');
      return;
    }

    if (startTime >= endTime) {
      setError('End time must be after start time.');
      return;
    }

    const [startH, startM] = startTime.split(':').map(Number);
    const [endH, endM] = endTime.split(':').map(Number);
    const startMinutes = startH * 60 + startM;
    const endMinutes = endH * 60 + endM;

    // Constraint 1: Regular lecture must be before 6:00 PM (18:00 = 1080 min)
    const sixPM = 18 * 60;
    if (sessionType === 'class') {
      if (endMinutes > sixPM || startMinutes >= sixPM) {
        setError('Time Policy Violation: Regular course lectures must be scheduled strictly BEFORE 6:00 PM (18:00).');
        return;
      }
    }

    // Constraint 2: Practice session must be after 6:30 PM (18:30 = 1110 min)
    const sixThirtyPM = 18 * 60 + 30;
    if (sessionType === 'practice') {
      if (startMinutes < sixThirtyPM) {
        setError('Time Policy Violation: Practice & lab sessions must be scheduled strictly AFTER 6:30 PM (18:30).');
        return;
      }
    }

    let updatedList;
    if (editingSlot) {
      // Update existing slot
      updatedList = timetables.map(slot => {
        if (slot.id === editingSlot.id) {
          return {
            ...slot,
            courseTitle,
            sessionType,
            day,
            startTime,
            endTime,
            room,
            instructor: teacherName,
            teacherId
          };
        }
        return slot;
      });
      setSuccess(`Your timetable for "${courseTitle}" on ${day} has been updated successfully!`);
    } else {
      // Add new slot customized by teacher
      const matchedCourse = myCourses.find(c => c.title === courseTitle);
      const newSlot = {
        id: Date.now(),
        courseId: matchedCourse ? matchedCourse.id : 101,
        courseTitle,
        sessionType,
        day,
        startTime,
        endTime,
        room,
        instructor: teacherName,
        teacherId
      };
      updatedList = [...timetables, newSlot];
      setSuccess(`New ${sessionType === 'class' ? 'lecture' : 'practice lab'} slot added to your personal schedule!`);
    }

    setTimetables(updatedList);
    localStorage.setItem('courseTimetables', JSON.stringify(updatedList));

    setTimeout(() => {
      setShowModal(false);
      setEditingSlot(null);
      setSuccess('');
    }, 1200);
  };

  const handleDeleteSlot = (id) => {
    if (!window.confirm('Are you sure you want to remove this slot from your timetable?')) return;
    const updated = timetables.filter(slot => slot.id !== id);
    setTimetables(updated);
    localStorage.setItem('courseTimetables', JSON.stringify(updated));
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 flex items-center gap-1">
              <Sliders size={12} /> Faculty Schedule Customizer
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">My Teaching Timetable</h1>
          <p className="text-gray-600 mt-1">
            Adjust and customize your lecture hours and practice sessions according to your personal availability.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition-colors shadow-sm cursor-pointer shrink-0"
        >
          <Plus size={18} /> Add / Adjust Schedule Slot
        </button>
      </div>

      {/* Teacher Schedule Overview Banner */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-blue-100 text-xs font-medium uppercase tracking-wider">
            <Sparkles size={14} /> Teacher Schedule Independence
          </div>
          <h2 className="text-xl font-bold">Personalized Faculty Calendar for {teacherName}</h2>
          <p className="text-blue-100 text-xs max-w-xl leading-relaxed">
            You have full autonomy to move lecture slots before 6:00 PM or organize evening practice labs after 6:30 PM. All adjustments update student and administration views in real-time.
          </p>
        </div>

        <div className="flex items-center gap-4 shrink-0 bg-white/10 backdrop-blur-xs p-4 rounded-xl border border-white/20">
          <div className="text-center px-2">
            <span className="block text-2xl font-extrabold">{mySlots.length}</span>
            <span className="text-[11px] text-blue-200">Total Slots</span>
          </div>
          <div className="h-8 w-px bg-white/20"></div>
          <div className="text-center px-2">
            <span className="block text-2xl font-extrabold">
              {mySlots.filter(s => s.sessionType === 'class').length}
            </span>
            <span className="text-[11px] text-blue-200">Lectures (&lt; 6 PM)</span>
          </div>
          <div className="h-8 w-px bg-white/20"></div>
          <div className="text-center px-2">
            <span className="block text-2xl font-extrabold">
              {mySlots.filter(s => s.sessionType === 'practice').length}
            </span>
            <span className="text-[11px] text-blue-200">Labs (&gt; 6:30 PM)</span>
          </div>
        </div>
      </div>

      {/* Constraints Guidelines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-900">
          <Sun className="text-blue-600 shrink-0 mt-0.5" size={18} />
          <div>
            <span className="font-bold block text-sm mb-0.5">Daytime Lectures (Your Choice &lt; 6:00 PM)</span>
            Choose any preferred teaching window between <strong>08:00 AM and 06:00 PM</strong>.
          </div>
        </div>

        <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-start gap-3 text-xs text-purple-900">
          <Moon className="text-purple-600 shrink-0 mt-0.5" size={18} />
          <div>
            <span className="font-bold block text-sm mb-0.5">Evening Practice Sessions (Your Choice &gt; 6:30 PM)</span>
            Schedule your interactive coding labs and student mentoring between <strong>06:30 PM and 10:30 PM</strong>.
          </div>
        </div>
      </div>

      {/* Weekly Schedule Display by Day */}
      <div className="space-y-6">
        {daysOfWeek.map((day) => {
          const daySlots = mySlots
            .filter(slot => slot.day === day)
            .sort((a, b) => a.startTime.localeCompare(b.startTime));

          return (
            <div key={day} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              <div className="bg-gray-50/80 px-6 py-3.5 border-b border-gray-200 flex items-center justify-between">
                <h3 className="font-bold text-gray-900 text-base flex items-center gap-2">
                  <Calendar size={18} className="text-blue-600" />
                  {day}
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                  {daySlots.length} {daySlots.length === 1 ? 'Session' : 'Sessions'}
                </span>
              </div>

              <div className="p-6">
                {daySlots.length === 0 ? (
                  <div className="flex items-center justify-between text-xs text-gray-400 py-1">
                    <span>No classes scheduled on {day}. Enjoy your research / preparation time!</span>
                    <button
                      onClick={() => {
                        handleOpenModal({ day });
                      }}
                      className="text-blue-600 hover:underline font-semibold cursor-pointer"
                    >
                      + Schedule slot on {day}
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {daySlots.map((slot) => (
                      <div
                        key={slot.id}
                        className={`p-5 rounded-xl border transition-all relative flex flex-col justify-between ${
                          slot.sessionType === 'class'
                            ? 'bg-blue-50/40 border-blue-200 hover:border-blue-400 shadow-2xs'
                            : 'bg-purple-50/40 border-purple-200 hover:border-purple-400 shadow-2xs'
                        }`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase flex items-center gap-1 ${
                              slot.sessionType === 'class'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-purple-100 text-purple-800'
                            }`}>
                              {slot.sessionType === 'class' ? <Sun size={11} /> : <Moon size={11} />}
                              {slot.sessionType === 'class' ? 'Class (< 6:00 PM)' : 'Practice Lab (> 6:30 PM)'}
                            </span>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => handleOpenModal(slot)}
                                className="text-gray-400 hover:text-blue-600 p-1 transition-colors cursor-pointer"
                                title="Adjust this slot"
                              >
                                <Edit2 size={15} />
                              </button>
                              <button
                                onClick={() => handleDeleteSlot(slot.id)}
                                className="text-gray-400 hover:text-red-600 p-1 transition-colors cursor-pointer"
                                title="Delete this slot"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </div>

                          <h4 className="font-bold text-gray-900 text-base mb-1">{slot.courseTitle}</h4>
                          <div className="flex items-center gap-1.5 font-bold text-gray-800 text-sm mt-2">
                            <Clock size={16} className={slot.sessionType === 'class' ? 'text-blue-600' : 'text-purple-600'} />
                            <span>{slot.startTime} – {slot.endTime}</span>
                          </div>
                        </div>

                        <div className="mt-4 pt-3 border-t border-gray-200/60 flex items-center justify-between text-xs text-gray-500">
                          <span>Venue: <strong className="text-gray-700">{slot.room}</strong></span>
                          <button
                            onClick={() => handleOpenModal(slot)}
                            className="text-xs font-semibold text-blue-600 hover:underline cursor-pointer"
                          >
                            Reschedule
                          </button>
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

      {/* Adjust / Add Slot Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-gray-50">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <Sliders size={18} className="text-blue-600" />
                {editingSlot?.id ? 'Adjust Teaching Slot' : 'Add Custom Teaching Slot'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveSlot} className="p-6 space-y-4">
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
                  name="courseTitle"
                  required
                  defaultValue={editingSlot?.courseTitle || myCourses[0]?.title}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                >
                  {myCourses.map(c => (
                    <option key={c.id} value={c.title}>{c.title}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Session Type *</label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-blue-50/50 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50">
                    <input
                      type="radio"
                      name="sessionType"
                      value="class"
                      defaultChecked={!editingSlot || editingSlot.sessionType === 'class'}
                      className="text-blue-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-gray-900 block">Daytime Class</span>
                      <span className="text-[10px] text-gray-500">Schedule &lt; 6:00 PM</span>
                    </div>
                  </label>

                  <label className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-purple-50/50 has-[:checked]:border-purple-500 has-[:checked]:bg-purple-50">
                    <input
                      type="radio"
                      name="sessionType"
                      value="practice"
                      defaultChecked={editingSlot?.sessionType === 'practice'}
                      className="text-purple-600"
                    />
                    <div>
                      <span className="text-xs font-bold text-gray-900 block">Practice / Lab</span>
                      <span className="text-[10px] text-gray-500">Schedule &gt; 6:30 PM</span>
                    </div>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Day of the Week *</label>
                  <select
                    name="day"
                    defaultValue={editingSlot?.day || 'Monday'}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-blue-500 focus:border-blue-500"
                  >
                    {daysOfWeek.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Room / Virtual Link</label>
                  <input
                    name="room"
                    type="text"
                    defaultValue={editingSlot?.room || 'Lecture Hall 2'}
                    placeholder="e.g., Room 204 / Google Meet"
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
                    defaultValue={editingSlot?.startTime || '10:00'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">End Time *</label>
                  <input
                    name="endTime"
                    type="time"
                    required
                    defaultValue={editingSlot?.endTime || '11:30'}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 text-[11px] text-gray-500 space-y-1">
                <p>• <strong>Lecture Policy</strong>: Must conclude before 6:00 PM.</p>
                <p>• <strong>Practice Policy</strong>: Must commence after 6:30 PM.</p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 shadow-sm cursor-pointer"
                >
                  Save Schedule Preference
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherTimetable;

