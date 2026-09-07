import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Navbar from './Navbar';

const DashboardLayout = ({ role }) => {
  return (
    <div className="flex h-screen overflow-hidden bg-white selection:bg-blue-100 selection:text-blue-900">
      <Sidebar role={role} />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar role={role} />
        <main className="flex-1 overflow-y-auto p-6 bg-gradient-mesh">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;

