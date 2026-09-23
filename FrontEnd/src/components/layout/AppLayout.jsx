import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import SessionTimeoutManager from '../common/SessionTimeoutManager';

export default function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="app-shell">
      <SessionTimeoutManager />
      <Sidebar isOpen={isSidebarOpen} onClose={closeSidebar} />
      <div className="app-main-canvas">
        <Header onToggleSidebar={toggleSidebar} />
        <Outlet />
      </div>
    </div>
  );
}
