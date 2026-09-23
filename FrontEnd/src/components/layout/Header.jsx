import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Bell, Menu, ChevronDown } from 'lucide-react';

export default function Header({ onToggleSidebar }) {
  const [userInfo, setUserInfo] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.fullName) {
          const name = parsed.fullName.trim();
          const parts = name.split(' ').filter(Boolean);
          const initials = parts.length > 1
            ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
            : name.substring(0, 2).toUpperCase();
          return { name, initials };
        }
      }
    } catch (e) {}
    return { name: 'Hemang Singh', initials: 'HS' };
  });

  useEffect(() => {
    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || JSON.parse(localStorage.getItem('fin_user') || '{}');
        if (user.fullName) {
          const name = user.fullName.trim();
          const parts = name.split(' ').filter(Boolean);
          const initials = parts.length > 1
            ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
            : name.substring(0, 2).toUpperCase();
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
