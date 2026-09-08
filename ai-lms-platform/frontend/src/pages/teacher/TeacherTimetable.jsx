import React, { useState, useEffect } from 'react';
import { Clock, Calendar, AlertCircle, CheckCircle, Sun, Moon, BookOpen, X, Sparkles, AlertTriangle, MessageSquare, Undo2, Info } from 'lucide-react';

const TeacherTimetable = () => {
  const [timetables, setTimetables] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [rescheduledList, setRescheduledList] = useState([]);
  const [showRescheduleModal, setShowRescheduleModal] = useState(false);
  const [selectedSlotForReschedule, setSelectedSlotForReschedule] = useState(null);
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

    // 2. Load all default timetables and strictly retain only slots whose course is approved by the administrator
    const allTimetables = JSON.parse(localStorage.getItem('courseTimetables') || '[]');
    const approvedOnlyTimetables = allTimetables.filter(slot => 
      approved.some(ac => ac.id === slot.courseId || ac.title?.toLowerCase() === slot.courseTitle?.toLowerCase())
    );
    setTimetables(approvedOnlyTimetables);

    // 3. Load Rescheduled Classes
    const savedRescheduled = JSON.parse(localStorage.getItem('rescheduledClasses') || '[]');
    setRescheduledList(savedRescheduled);
  };

  useEffect(() => {
    loadData();

    const handleUpdate = () => loadData();
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('rescheduledClassesUpdated', handleUpdate);
    window.addEventListener('approvedCoursesUpdated', handleUpdate);

    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('rescheduledClassesUpdated', handleUpdate);
      window.removeEventListener('approvedCoursesUpdated', handleUpdate);
    };
  }, []);

  // Filter slots strictly for this teacher from the approved courses
  const mySlots = timetables.filter(slot => {
    if (slot.instructor === teacherName) return true;
    if (slot.teacherId && slot.teacherId.toString() === teacherId.toString()) return true;
    const lastName = teacherName.split(' ').pop();
    return slot.instructor && slot.instructor.includes(lastName);
  });

  const handleOpenRescheduleModal = (slot) => {
    setSelectedSlotForReschedule(slot);
    setError('');
    setSuccess('');
    setShowRescheduleModal(true);
  };

  const handleSaveReschedule = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!selectedSlotForReschedule) return;

    const form = e.target;
    const newDate = form.newDate.value;
    const newDay = form.newDay.value;
    const newStartTime = form.newStartTime.value;
    const newEndTime = form.newEndTime.value;
    const room = form.room.value.trim() || selectedSlotForReschedule.room || 'Online Meet Room';
    const message = form.message.value.trim();

    if (!newDate) {
      setError('Please select the rescheduled class date.');
      return;
    }

    if (!newStartTime || !newEndTime) {
      setError('Please select valid start and end times.');
      return;
    }

    if (newStartTime >= newEndTime) {
      setError('End time must be after start time.');
      return;
    }

    if (!message) {
      setError('Please provide a message or reason to inform the students about the reschedule.');
      return;
    }

    const [startH, startM] = newStartTime.split(':').map(Number);
    const [endH, endM] = newEndTime.split(':').map(Number);
    const startMinutes = startH * 60 + startM;
    const endMinutes = endH * 60 + endM;

    // Time Policy Rules
    const sixPM = 18 * 60;
    if (selectedSlotForReschedule.sessionType === 'class') {
      if (endMinutes > sixPM || startMinutes >= sixPM) {
        setError('Time Policy Violation: Regular course lectures must be scheduled strictly BEFORE 6:00 PM (18:00).');
        return;
      }
    }

    const sixThirtyPM = 18 * 60 + 30;
    if (selectedSlotForReschedule.sessionType === 'practice') {
      if (startMinutes < sixThirtyPM) {
        setError('Time Policy Violation: Practice & lab sessions must be scheduled strictly AFTER 6:30 PM (18:30).');
        return;
      }
    }

    const currentRescheduled = JSON.parse(localStorage.getItem('rescheduledClasses') || '[]');
    // Remove any previous active reschedule for this slot
    const filteredRescheduled = currentRescheduled.filter(r => r.slotId !== selectedSlotForReschedule.id);

    const newRescheduleRecord = {
      id: Date.now(),
      slotId: selectedSlotForReschedule.id,
      courseId: selectedSlotForReschedule.courseId,
      courseTitle: selectedSlotForReschedule.courseTitle,
      sessionType: selectedSlotForReschedule.sessionType,
      originalDay: selectedSlotForReschedule.day,
      originalStartTime: selectedSlotForReschedule.startTime,
      originalEndTime: selectedSlotForReschedule.endTime,
      newDate,
      newDay,
      newStartTime,
      newEndTime,
      room,
      message,
      teacherName: teacherName,
      teacherId: teacherId,
      createdAt: new Date().toISOString()
    };

    filteredRescheduled.push(newRescheduleRecord);
    localStorage.setItem('rescheduledClasses', JSON.stringify(filteredRescheduled));
    setRescheduledList(filteredRescheduled);

    window.dispatchEvent(new Event('rescheduledClassesUpdated'));

    setSuccess(`Class rescheduled successfully! A notice has been broadcast to all enrolled students.`);

    setTimeout(() => {
      setShowRescheduleModal(false);
      setSelectedSlotForReschedule(null);
      setSuccess('');
    }, 1400);
  };

  const handleCancelReschedule = (slotId) => {
    if (!window.confirm('Cancel this reschedule and revert back to the default institutional timetable?')) return;
    const currentRescheduled = JSON.parse(localStorage.getItem('rescheduledClasses') || '[]');
    const updated = currentRescheduled.filter(r => r.slotId !== slotId);
    localStorage.setItem('rescheduledClasses', JSON.stringify(updated));
    setRescheduledList(updated);
    window.dispatchEvent(new Event('rescheduledClassesUpdated'));
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 flex items-center gap-1">
              <Calendar size={12} /> Faculty Timetable & Reschedule Center
            </span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Faculty Teaching Timetable</h1>
          <p className="text-gray-600 mt-1">
            The default timetable is officially set and approved by the Administrator. If needed, you may reschedule a class session with a notification message to enrolled students.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded-lg">
          <Info size={16} className="shrink-0 text-amber-600" />
          <span>Default timetable is locked by Administrator. Rescheduled classes notify students directly.</span>
        </div>
      </div>

      {/* Teacher Reschedule Notice Banner */}
      <div className="bg-gradient-to-r from-blue-700 to-indigo-800 rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-blue-200 text-xs font-semibold uppercase tracking-wider">
            <Sparkles size={14} /> Official Faculty Schedule
          </div>
          <h2 className="text-xl font-bold">Timetable for {teacherName}</h2>
          <p className="text-blue-100 text-xs max-w-xl leading-relaxed">
            Institutional courses and their default schedule are locked to maintain curriculum compliance. When unforeseen conflicts arise, use the <strong>"Reschedule Class"</strong> button on any slot to assign a new time and broadcast a message to your students.
          </p>
        </div>

        <div className="flex items-center gap-4 shrink-0 bg-white/10 backdrop-blur-xs p-4 rounded-xl border border-white/20">
          <div className="text-center px-2">
            <span className="block text-2xl font-extrabold">{mySlots.length}</span>
            <span className="text-[11px] text-blue-200">Default Slots</span>
          </div>
          <div className="h-8 w-px bg-white/20"></div>
          <div className="text-center px-2">
            <span className="block text-2xl font-extrabold text-amber-300">
              {rescheduledList.filter(r => mySlots.some(s => s.id === r.slotId)).length}
            </span>
            <span className="text-[11px] text-amber-200">Rescheduled</span>
          </div>
        </div>
      </div>

      {/* Constraints Guidelines */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-900">
          <Sun className="text-blue-600 shrink-0 mt-0.5" size={18} />
          <div>
            <span className="font-bold block text-sm mb-0.5">Daytime Lectures (Must be &lt; 6:00 PM)</span>
            Lecture sessions can be rescheduled strictly between <strong>08:00 AM and 06:00 PM</strong>.
          </div>
        </div>

        <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-start gap-3 text-xs text-purple-900">
          <Moon className="text-purple-600 shrink-0 mt-0.5" size={18} />
          <div>
            <span className="font-bold block text-sm mb-0.5">Evening Practice Sessions (Must be &gt; 6:30 PM)</span>
            Practice and hands-on coding labs can be rescheduled strictly between <strong>06:30 PM and 10:30 PM</strong>.
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
                  {daySlots.length} Approved {daySlots.length === 1 ? 'Session' : 'Sessions'}
                </span>
              </div>

              <div className="p-6">
                {daySlots.length === 0 ? (
                  <div className="text-xs text-gray-400 py-1 italic">
                    No approved classes scheduled on {day}.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {daySlots.map((slot) => {
                      const activeReschedule = rescheduledList.find(r => r.slotId === slot.id);

                      return (
                        <div
                          key={slot.id}
                          className={`p-5 rounded-xl border transition-all relative flex flex-col justify-between ${
                            activeReschedule
                              ? 'bg-amber-50/60 border-amber-300 shadow-sm'
                              : slot.sessionType === 'class'
                              ? 'bg-blue-50/40 border-blue-200 hover:border-blue-300'
                              : 'bg-purple-50/40 border-purple-200 hover:border-purple-300'
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

                              {activeReschedule ? (
                                <span className="px-2 py-0.5 bg-amber-200 text-amber-900 rounded font-bold text-[10px] flex items-center gap-1">
                                  <AlertTriangle size={11} /> Rescheduled
                                </span>
                              ) : (
                                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                                  Approved Default
                                </span>
                              )}
                            </div>

                            <h4 className="font-bold text-gray-900 text-base mb-1">{slot.courseTitle}</h4>
                            
                            {/* Schedule details */}
                            {activeReschedule ? (
                              <div className="space-y-2 mt-2">
                                <div className="p-2.5 bg-white/80 rounded-lg border border-amber-200 text-xs">
                                  <div className="text-gray-400 line-through text-[11px]">
                                    Default: {slot.day}, {slot.startTime} – {slot.endTime}
                                  </div>
                                  <div className="font-bold text-amber-900 text-sm mt-0.5 flex items-center gap-1.5">
                                    <Clock size={14} className="text-amber-600" />
                                    <span>New: {activeReschedule.newDay} ({activeReschedule.newDate})</span>
                                  </div>
                                  <div className="font-semibold text-amber-800 text-xs mt-0.5 pl-5">
                                    {activeReschedule.newStartTime} – {activeReschedule.newEndTime}
                                  </div>
                                </div>

                                <div className="p-2 bg-amber-100/70 rounded-md border border-amber-200 text-xs text-amber-900">
                                  <p className="font-semibold flex items-center gap-1 text-[11px] mb-0.5">
                                    <MessageSquare size={12} /> Message to Students:
                                  </p>
                                  <p className="italic text-[11px]">"{activeReschedule.message}"</p>
                                </div>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 font-bold text-gray-800 text-sm mt-2">
                                <Clock size={16} className={slot.sessionType === 'class' ? 'text-blue-600' : 'text-purple-600'} />
                                <span>{slot.startTime} – {slot.endTime}</span>
                              </div>
                            )}
                          </div>

                          <div className="mt-4 pt-3 border-t border-gray-200/60 flex items-center justify-between text-xs text-gray-500">
                            <span>Venue: <strong className="text-gray-700">{activeReschedule ? activeReschedule.room : slot.room}</strong></span>
                            
                            {activeReschedule ? (
                              <button
                                onClick={() => handleCancelReschedule(slot.id)}
                                className="flex items-center gap-1 text-xs font-semibold text-red-600 hover:text-red-800 cursor-pointer"
                                title="Revert to default schedule"
                              >
                                <Undo2 size={13} /> Revert
                              </button>
                            ) : (
                              <button
                                onClick={() => handleOpenRescheduleModal(slot)}
                                className="px-2.5 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded font-semibold text-xs cursor-pointer transition-colors"
                              >
                                Reschedule Class
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Reschedule Class Modal */}
      {showRescheduleModal && selectedSlotForReschedule && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center p-5 border-b border-gray-100 bg-amber-50/70">
              <div>
                <h3 className="font-bold text-amber-950 flex items-center gap-2">
                  <Calendar size={18} className="text-amber-700" />
                  Reschedule Class Session
                </h3>
                <p className="text-xs text-amber-800 mt-0.5">
                  Default timetable remains intact. A reschedule announcement will be displayed on student dashboards.
                </p>
              </div>
              <button onClick={() => setShowRescheduleModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveReschedule} className="p-6 space-y-4">
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

              {/* Course and Default Timetable Overview (Read Only) */}
              <div className="p-3.5 bg-gray-50 rounded-lg border border-gray-200 space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-gray-900 text-sm">{selectedSlotForReschedule.courseTitle}</span>
                  <span className={`px-2 py-0.5 rounded font-bold uppercase text-[9px] ${
                    selectedSlotForReschedule.sessionType === 'class' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                  }`}>
                    {selectedSlotForReschedule.sessionType === 'class' ? 'Lecture' : 'Practice Lab'}
                  </span>
                </div>
                <p className="text-gray-600">
                  Default Scheduled Slot: <strong className="text-gray-800">{selectedSlotForReschedule.day} • {selectedSlotForReschedule.startTime} – {selectedSlotForReschedule.endTime}</strong>
                </p>
                <p className="text-[11px] text-gray-500">
                  Approved Room: {selectedSlotForReschedule.room}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Rescheduled Date *</label>
                  <input
                    name="newDate"
                    type="date"
                    required
                    min={new Date().toISOString().split('T')[0]}
                    defaultValue={new Date(Date.now() + 86400000).toISOString().split('T')[0]}
                    onChange={(e) => {
                      if (e.target.value) {
                        const dateObj = new Date(e.target.value + 'T00:00:00');
                        const dayName = dateObj.toLocaleDateString('en-US', { weekday: 'long' });
                        const daySelect = e.target.form.elements['newDay'];
                        if (daySelect && daysOfWeek.includes(dayName)) {
                          daySelect.value = dayName;
                        }
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Day of the Week *</label>
                  <select
                    name="newDay"
                    defaultValue={selectedSlotForReschedule.day}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                  >
                    {daysOfWeek.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    New Start Time * {selectedSlotForReschedule.sessionType === 'class' ? '(< 6 PM)' : '(> 6:30 PM)'}
                  </label>
                  <input
                    name="newStartTime"
                    type="time"
                    required
                    defaultValue={selectedSlotForReschedule.startTime}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">New End Time *</label>
                  <input
                    name="newEndTime"
                    type="time"
                    required
                    defaultValue={selectedSlotForReschedule.endTime}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">New Venue / Room / Online Link</label>
                <input
                  name="room"
                  type="text"
                  defaultValue={selectedSlotForReschedule.room}
                  placeholder="e.g., Room 304 or Zoom / Google Meet Link"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Message / Reason for Students *
                </label>
                <textarea
                  name="message"
                  required
                  rows="3"
                  placeholder="e.g., This lecture is rescheduled due to faculty attendance at the academic council. Please join via the updated link."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                ></textarea>
                <span className="text-[11px] text-gray-500">
                  This message will appear prominently on the enrolled students' dashboards.
                </span>
              </div>

              <div className="p-3 bg-amber-50/70 rounded-lg border border-amber-200 text-[11px] text-amber-900 space-y-1">
                <p>• <strong>Notice</strong>: The default timetable approved by the administrator is NOT modified or erased.</p>
                <p>• <strong>Lecture Rule</strong>: Daytime lectures must conclude before 6:00 PM.</p>
                <p>• <strong>Practice Rule</strong>: Evening labs must commence after 6:30 PM.</p>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowRescheduleModal(false)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-amber-600 text-white rounded-lg text-sm font-bold hover:bg-amber-700 shadow-sm cursor-pointer"
                >
                  Confirm & Broadcast Reschedule
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

