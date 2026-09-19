import React from 'react';
import { NavLink } from 'react-router-dom';
import { Search, Bell, Menu, ChevronDown } from 'lucide-react';

export default function Header({ onToggleSidebar }) {
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
            HS
          </div>
          <div className="user-info">
            <span className="user-name">Hemang Singh</span>
            <span className="user-role">Individual Applicant</span>
          </div>
          <ChevronDown size={14} className="user-chevron" aria-hidden="true" />
        </NavLink>
      </div>
    </header>
  );
}
