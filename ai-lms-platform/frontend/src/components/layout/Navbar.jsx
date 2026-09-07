import React, { useState, useEffect, useRef } from 'react';
import { LogOut, Bell, User, MessageSquare, Check, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Navbar = ({ role }) => {
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const notifRef = useRef(null);

  useEffect(() => {
    // Only fetch notifications for students
    if (role === 'student') {
      const userEmail = localStorage.getItem('userEmail');
      if (userEmail) {
        const notifs = JSON.parse(localStorage.getItem(`studentNotifications_${userEmail}`) || '[]');
        setNotifications(notifs.sort((a, b) => b.id - a.id));
      }
    }

    const handleClickOutside = (event) => {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [role]);

  const handleLogout = () => {
    navigate('/login');
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  const markAllAsRead = () => {
    const updated = notifications.map(n => ({ ...n, read: true }));
    setNotifications(updated);
    const userEmail = localStorage.getItem('userEmail');
    if (userEmail) {
      localStorage.setItem(`studentNotifications_${userEmail}`, JSON.stringify(updated));
    }
  };

  const clearNotifications = () => {
    setNotifications([]);
    const userEmail = localStorage.getItem('userEmail');
    if (userEmail) {
      localStorage.setItem(`studentNotifications_${userEmail}`, JSON.stringify([]));
    }
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 relative z-50">
      <div className="flex items-center text-sm font-medium text-gray-500">
        <span className="capitalize">{role} View</span>
      </div>
      
      <div className="flex items-center gap-4">
        {role === 'student' && (
          <div className="relative" ref={notifRef}>
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className="relative text-gray-500 hover:text-gray-700 p-2 rounded-full hover:bg-gray-100 cursor-pointer transition-colors"
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white"></span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden z-50">
                <div className="flex items-center justify-between p-3 border-b border-gray-100 bg-gray-50">
                  <h3 className="font-bold text-gray-900 text-sm">Notifications</h3>
                  <div className="flex gap-2">
                    {unreadCount > 0 && (
                      <button onClick={markAllAsRead} className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1" title="Mark all read">
                        <Check size={12} />
                      </button>
                    )}
                    {notifications.length > 0 && (
                      <button onClick={clearNotifications} className="text-xs text-gray-400 hover:text-red-600 transition-colors" title="Clear all">
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
                
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="p-6 text-center text-gray-500 text-sm">
                      <Bell size={24} className="mx-auto mb-2 text-gray-300" />
                      No new notifications
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-50">
                      {notifications.map(notif => (
                        <div key={notif.id} className={`p-3 hover:bg-gray-50 transition-colors ${!notif.read ? 'bg-blue-50/30' : ''}`}>
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0 mt-0.5 text-blue-600">
                              <MessageSquare size={14} />
                            </div>
                            <div>
                              <div className="flex items-center justify-between gap-2 mb-0.5">
                                <span className="font-semibold text-gray-900 text-sm">{notif.sender}</span>
                                <span className="text-[10px] text-gray-400">
                                  {new Date(notif.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                              <p className="text-sm text-gray-600 line-clamp-3 leading-relaxed">{notif.message}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 border-l pl-4 border-gray-200">
          <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center cursor-pointer hover:bg-blue-200 transition-colors">
            <User size={16} />
          </div>
          <span className="text-sm font-medium text-gray-700 hidden sm:block">
            {localStorage.getItem('userName') || (role === 'teacher' ? 'Prof. Smith' : 'Alex Student')}
          </span>
          <button 
            onClick={handleLogout}
            className="ml-2 text-gray-500 hover:text-red-600 p-2 rounded-full hover:bg-red-50 cursor-pointer"
            title="Log out"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Navbar;

