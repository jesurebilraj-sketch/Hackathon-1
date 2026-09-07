import React from 'react';
import { LogOut, Bell, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Navbar = ({ role }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    navigate('/login');
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center text-sm font-medium text-gray-500">
        <span className="capitalize">{role} View</span>
      </div>
      
      <div className="flex items-center gap-4">
        <button className="text-gray-500 hover:text-gray-700 p-2 rounded-full hover:bg-gray-100">
          <Bell size={20} />
        </button>
        <div className="flex items-center gap-2 border-l pl-4 border-gray-200">
          <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center">
            <User size={16} />
          </div>
          <span className="text-sm font-medium text-gray-700 hidden sm:block">
            {localStorage.getItem('userName') || (role === 'teacher' ? 'Prof. Smith' : 'Alex Student')}
          </span>
          <button 
            onClick={handleLogout}
            className="ml-2 text-gray-500 hover:text-red-600 p-2 rounded-full hover:bg-red-50"
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

