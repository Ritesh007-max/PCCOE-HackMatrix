import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import SessionTimeoutManager from '../common/SessionTimeoutManager';
import FinAssistantModal from '../chat/FinAssistantModal';

export default function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isChatMinimized, setIsChatMinimized] = useState(false);

  const toggleSidebar = () => setIsSidebarOpen((prev) => !prev);
  const closeSidebar = () => setIsSidebarOpen(false);

  const toggleChat = () => {
    setIsChatOpen((prev) => !prev);
    setIsChatMinimized(false);
  };

  const closeChat = () => {
    setIsChatOpen(false);
    setIsChatMinimized(false);
  };

  const toggleMinimizeChat = () => {
    setIsChatMinimized((prev) => !prev);
  };

  // Allow other components to trigger chat popup
  useEffect(() => {
    const handleOpenChat = () => {
      setIsChatOpen(true);
      setIsChatMinimized(false);
    };
    window.addEventListener('open_fin_chat', handleOpenChat);
    return () => window.removeEventListener('open_fin_chat', handleOpenChat);
  }, []);

  return (
    <div className="app-shell">
      <SessionTimeoutManager />
      <Sidebar isOpen={isSidebarOpen} onClose={closeSidebar} />
      <div className="app-main-canvas">
        <Header
          onToggleSidebar={toggleSidebar}
          onToggleChat={toggleChat}
          isChatOpen={isChatOpen}
        />
        <Outlet />
      </div>

      {/* FIN Assistant (AI) Pop-up Modal */}
      <FinAssistantModal
        isOpen={isChatOpen}
        onClose={closeChat}
        isMinimized={isChatMinimized}
        onToggleMinimize={toggleMinimizeChat}
      />
    </div>
  );
}


