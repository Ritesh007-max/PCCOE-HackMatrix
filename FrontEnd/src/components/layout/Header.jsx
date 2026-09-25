import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Bell, Menu, ChevronDown, Sparkles } from 'lucide-react';
import { resolveDisplayName } from '../../services/authService';

export default function Header({ onToggleSidebar, onToggleChat, isChatOpen }) {
  const [userInfo, setUserInfo] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        const resolved = resolveDisplayName(parsed, parsed?.email);
        if (resolved) {
          const fullName = resolved.trim();
          const parts = fullName.split(' ').filter(Boolean);
          const initials = fullName.length >= 2 ? fullName.substring(0, 2).toUpperCase() : fullName.toUpperCase();
          const name = parts[0] || fullName;
          return { name, initials };
        }
      }
    } catch (e) {}
    return { name: 'Hemang', initials: 'HE' };
  });

  useEffect(() => {
    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || JSON.parse(localStorage.getItem('fin_user') || '{}');
        const resolved = resolveDisplayName(user, user?.email);
        if (resolved) {
          const fullName = resolved.trim();
          const parts = fullName.split(' ').filter(Boolean);
          const initials = fullName.length >= 2 ? fullName.substring(0, 2).toUpperCase() : fullName.toUpperCase();
          const name = parts[0] || fullName;
          setUserInfo({ name, initials });
        }
      } catch (err) {}
    };

    window.addEventListener('fin_user_updated', handleUserUpdate);
    window.addEventListener('storage', handleUserUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleUserUpdate);
      window.removeEventListener('storage', handleUserUpdate);
    };
  }, []);

  return (
    <header className="app-header">
      <div className="header-left">
        <button
          type="button"
          className="menu-toggle-btn"
          onClick={onToggleSidebar}
          aria-label="Open sidebar menu"
        >
          <Menu size={20} />
        </button>

        <div className="global-search-container" role="search">
          <Search size={17} className="search-icon" aria-hidden="true" />
          <input
            type="search"
            className="global-search-input"
            placeholder="Search schemes, policies, or keywords..."
            aria-label="Search schemes, policies, or keywords"
          />
          <div className="search-shortcut-badge" aria-hidden="true">
            <span>⌘ K</span>
          </div>
        </div>
      </div>

      <div className="header-right">
        <button
          type="button"
          className={`navbar-ai-assistant-btn ${isChatOpen ? 'active' : ''}`}
          onClick={onToggleChat}
          aria-label="Open FIN AI Assistant"
          title="Open FIN Assistant (AI)"
        >
          <span className="navbar-ai-sparkle-icon" aria-hidden="true">
            <Sparkles size={15} />
          </span>
          <span className="navbar-ai-btn-text">Ask FIN AI</span>
          <span className="navbar-ai-badge" aria-hidden="true">AI</span>
        </button>

        <button
          type="button"
          className="notification-btn"
          aria-label="Notifications (1 new notification)"
          title="Notifications"
        >
          <Bell size={18} />
          <span className="notification-red-dot" aria-hidden="true" />
        </button>

        <NavLink to="/profile" className="user-profile-badge" title="View Profile">
          <div className="user-avatar-hs" aria-hidden="true">
            {userInfo.initials}
          </div>
          <div className="user-info">
            <span className="user-name">{userInfo.name}</span>
            <span className="user-role">Individual Applicant</span>
          </div>
          <ChevronDown size={14} className="user-chevron" aria-hidden="true" />
        </NavLink>
      </div>
    </header>
  );
}
