import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import SessionTimeoutManager from '../common/SessionTimeoutManager';
import FinAssistantModal from '../chat/FinAssistantModal';
import { useUser } from '@clerk/react';
import { storeAuthSession } from '../../services/authService';

export default function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isChatMinimized, setIsChatMinimized] = useState(false);
  const { user: clerkUser, isLoaded: isClerkLoaded, isSignedIn: isClerkSignedIn } = useUser();

  // Sync Clerk profile data into app storage
  useEffect(() => {
    if (isClerkLoaded && isClerkSignedIn && clerkUser) {
      const email = clerkUser.primaryEmailAddress?.emailAddress || '';
      const fullName = clerkUser.fullName || clerkUser.firstName || 'Google Citizen';
      storeAuthSession({
        user: {
          id: clerkUser.id,
          email,
          fullName,
          avatarUrl: clerkUser.imageUrl,
        },
        accessToken: 'clerk-google-oauth-token',
        fallbackName: fullName,
      });
    }
  }, [isClerkLoaded, isClerkSignedIn, clerkUser]);

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


