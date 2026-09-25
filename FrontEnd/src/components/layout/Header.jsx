import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Bell,
  Menu,
  ChevronDown,
  Sparkles,
  X,
  User,
  FileText,
  Briefcase,
  LogOut,
  CheckCircle2,
  Clock,
  Shield,
  ArrowRight,
} from 'lucide-react';
import { resolveDisplayName, logoutUser } from '../../services/authService';
import { SCHEMES } from '../../data/schemesData';

const DEFAULT_NOTIFICATIONS = [
  {
    id: 'notif-1',
    title: 'Application Status Updated',
    message: "Your application #APP-2026-8842 for PM Kisan Samman Nidhi is now 'Under Review'.",
    time: '10m ago',
    unread: true,
    type: 'status',
    link: '/applications',
  },
  {
    id: 'notif-2',
    title: 'New Scheme Matched',
    message: 'You qualify for National Apprenticeship Promotion Scheme (NAPS) based on your profile.',
    time: '2h ago',
    unread: true,
    type: 'scheme',
    link: '/discover',
  },
  {
    id: 'notif-3',
    title: 'Document Verified',
    message: 'Income Certificate (2025-26) was successfully verified with DBT portal.',
    time: '1d ago',
    unread: false,
    type: 'doc',
    link: '/documents',
  },
  {
    id: 'notif-4',
    title: 'Deadline Approaching',
    message: 'Digital India Internship application submission closes in 3 days.',
    time: '2d ago',
    unread: false,
    type: 'alert',
    link: '/discover',
  },
];

export default function Header({ onToggleSidebar, onToggleChat, isChatOpen }) {
  const navigate = useNavigate();

  // User State
  const [userInfo, setUserInfo] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        const resolved = resolveDisplayName(parsed, parsed?.email);
        const fullName = (resolved || parsed?.fullName || parsed?.name || 'Hemang Singh').trim();
        const parts = fullName.split(' ').filter(Boolean);
        const initials = fullName.length >= 2 ? fullName.substring(0, 2).toUpperCase() : fullName.toUpperCase();
        const name = parts[0] || fullName;
        const avatarUrl = parsed?.avatarUrl || parsed?.avatar_url || '';
        const role = parsed?.applicantType ? `${parsed.applicantType} Applicant` : 'Individual Applicant';
        const email = parsed?.email || 'hemang@example.com';
        const state = parsed?.state || 'Gujarat';
        return { name, fullName, initials, avatarUrl, role, email, state };
      }
    } catch (e) {}
    return {
      name: 'Hemang',
      fullName: 'Hemang Singh',
      initials: 'HE',
      avatarUrl: '',
      role: 'Individual Applicant',
      email: 'hemang@example.com',
      state: 'Gujarat',
    };
  });

  // Dropdown States
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [notifications, setNotifications] = useState(DEFAULT_NOTIFICATIONS);

  // Search States
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Refs for click outside
  const searchContainerRef = useRef(null);
  const searchInputRef = useRef(null);
  const notificationWrapperRef = useRef(null);
  const profileWrapperRef = useRef(null);

  // Unread notifications count
  const unreadCount = useMemo(() => {
    return notifications.filter((n) => n.unread).length;
  }, [notifications]);

  // Synchronize user updates
  useEffect(() => {
    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || JSON.parse(localStorage.getItem('fin_user') || '{}');
        const resolved = resolveDisplayName(user, user?.email);
        const fullName = (resolved || user?.fullName || user?.name || 'Hemang Singh').trim();
        const parts = fullName.split(' ').filter(Boolean);
        const initials = fullName.length >= 2 ? fullName.substring(0, 2).toUpperCase() : fullName.toUpperCase();
        const name = parts[0] || fullName;
        const avatarUrl = user?.avatarUrl || user?.avatar_url || '';
        const role = user?.applicantType ? `${user.applicantType} Applicant` : 'Individual Applicant';
        const email = user?.email || 'hemang@example.com';
        const state = user?.state || 'Gujarat';
        setUserInfo({ name, fullName, initials, avatarUrl, role, email, state });
      } catch (err) {}
    };

    window.addEventListener('fin_user_updated', handleUserUpdate);
    window.addEventListener('storage', handleUserUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleUserUpdate);
      window.removeEventListener('storage', handleUserUpdate);
    };
  }, []);

  // Click outside listener for all popovers
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setIsSearchOpen(false);
      }
      if (notificationWrapperRef.current && !notificationWrapperRef.current.contains(e.target)) {
        setIsNotificationOpen(false);
      }
      if (profileWrapperRef.current && !profileWrapperRef.current.contains(e.target)) {
        setIsProfileOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        setIsSearchOpen(true);
      } else if (e.key === 'Escape') {
        setIsSearchOpen(false);
        setIsNotificationOpen(false);
        setIsProfileOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Matching schemes based on query
  const matchingSchemes = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    return SCHEMES.filter((scheme) => {
      return (
        scheme.title?.toLowerCase().includes(q) ||
        scheme.subtitle?.toLowerCase().includes(q) ||
        scheme.description?.toLowerCase().includes(q) ||
        scheme.tags?.some((t) => t.toLowerCase().includes(q)) ||
        scheme.categories?.some((c) => c.toLowerCase().includes(q))
      );
    }).slice(0, 5);
  }, [searchQuery]);

  // Handle Search Submit (Enter)
  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearchOpen(false);
    navigate(`/discover?q=${encodeURIComponent(searchQuery.trim())}`);
  };

  // Handle Selecting a Scheme
  const handleSelectScheme = (schemeId) => {
    setIsSearchOpen(false);
    setSearchQuery('');
    navigate(`/schemes/${schemeId}`);
  };

  // Notification actions
  const toggleNotification = () => {
    setIsNotificationOpen((prev) => !prev);
    setIsProfileOpen(false);
    setIsSearchOpen(false);
  };

  const handleMarkAllAsRead = () => {
    setNotifications((prev) => prev.map((item) => ({ ...item, unread: false })));
  };

  const handleClearAllNotifications = () => {
    setNotifications([]);
  };

  const handleNotificationClick = (item) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, unread: false } : n))
    );
    setIsNotificationOpen(false);
    if (item.link) {
      navigate(item.link);
    }
  };

  // Profile Menu actions
  const toggleProfileMenu = () => {
    setIsProfileOpen((prev) => !prev);
    setIsNotificationOpen(false);
    setIsSearchOpen(false);
  };

  const handleLogout = async () => {
    setIsProfileOpen(false);
    try {
      await logoutUser();
      navigate('/login');
    } catch (e) {
      navigate('/login');
    }
  };

  return (
    <header className="app-header">
      {/* Left: Mobile Toggle & Active Global Search */}
      <div className="header-left">
        <button
          type="button"
          className="menu-toggle-btn"
          onClick={onToggleSidebar}
          aria-label="Open sidebar menu"
        >
          <Menu size={20} />
        </button>

        <div className="global-search-container" role="search" ref={searchContainerRef}>
          <Search size={17} className="search-icon" aria-hidden="true" />
          <input
            ref={searchInputRef}
            type="search"
            className="global-search-input"
            placeholder="Search schemes, policies, or keywords..."
            aria-label="Search schemes, policies, or keywords"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsSearchOpen(true);
            }}
            onFocus={() => {
              if (searchQuery.trim().length > 0) {
                setIsSearchOpen(true);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSearchSubmit(e);
              }
            }}
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => {
                setSearchQuery('');
                setIsSearchOpen(false);
                searchInputRef.current?.focus();
              }}
              aria-label="Clear search query"
            >
              <X size={14} />
            </button>
          )}
          <div
            className="search-shortcut-badge"
            aria-hidden="true"
            onClick={() => {
              searchInputRef.current?.focus();
              setIsSearchOpen(true);
            }}
            title="Press Cmd+K or Ctrl+K to search"
          >
            <span>⌘ K</span>
          </div>

          {/* Search Results Dropdown */}
          {isSearchOpen && searchQuery.trim().length > 0 && (
            <div className="global-search-dropdown" role="listbox" aria-label="Search schemes results">
              <div className="search-dropdown-header">
                <span className="search-dropdown-title">Matching Schemes</span>
                <span className="search-dropdown-count">
                  {matchingSchemes.length} {matchingSchemes.length === 1 ? 'match' : 'matches'}
                </span>
              </div>

              <div className="search-dropdown-results">
                {matchingSchemes.length > 0 ? (
                  matchingSchemes.map((scheme) => (
                    <div
                      key={scheme.id}
                      className="search-result-item"
                      onClick={() => handleSelectScheme(scheme.id)}
                      role="option"
                    >
                      <div className="search-result-icon-box">
                        <Sparkles size={15} />
                      </div>
                      <div className="search-result-info">
                        <div className="search-result-title-row">
                          <span className="search-result-name">{scheme.title}</span>
                          {scheme.benefitAmount && (
                            <span className="search-result-benefit">{scheme.benefitAmount}</span>
                          )}
                        </div>
                        <p className="search-result-desc">
                          {scheme.subtitle || scheme.description}
                        </p>
                        {scheme.tags && scheme.tags.length > 0 && (
                          <div className="search-result-tags">
                            {scheme.tags.slice(0, 2).map((t, idx) => (
                              <span key={idx} className="search-result-tag">
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="search-empty-state">
                    <p className="search-empty-title">
                      No schemes found for "<strong>{searchQuery}</strong>"
                    </p>
                    <p className="search-empty-hint">
                      Try searching 'kisan', 'student', 'loan', 'scholarship', or 'subsidy'.
                    </p>
                  </div>
                )}
              </div>

              <div className="search-dropdown-footer" onClick={handleSearchSubmit}>
                <span>Press <strong>↵ Enter</strong> to explore all schemes in Discover</span>
                <ArrowRight size={13} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: AI Assistant Button, Notifications Bell & Profile Badge */}
      <div className="header-right">
        {/* FIN AI Assistant Navbar Trigger */}
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

        {/* Notifications Popover Wrapper */}
        <div className="header-notification-wrapper" ref={notificationWrapperRef}>
          <button
            type="button"
            className={`notification-btn ${isNotificationOpen ? 'active' : ''}`}
            onClick={toggleNotification}
            aria-label={`Notifications (${unreadCount} unread)`}
            aria-expanded={isNotificationOpen}
            title="Notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && <span className="notification-red-dot" aria-hidden="true" />}
          </button>

          {/* Notifications Dropdown Popover */}
          {isNotificationOpen && (
            <div className="notification-popover" role="dialog" aria-label="Notifications panel">
              <div className="notification-popover-header">
                <div className="notif-header-title-box">
                  <h3 className="notif-popover-title">Notifications</h3>
                  {unreadCount > 0 && (
                    <span className="notif-unread-count-pill">{unreadCount} New</span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    className="notif-mark-read-action"
                    onClick={handleMarkAllAsRead}
                  >
                    <CheckCircle2 size={13} />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>

              <div className="notification-popover-list">
                {notifications.length === 0 ? (
                  <div className="notif-empty-state">
                    <CheckCircle2 size={24} className="notif-empty-icon" />
                    <p className="notif-empty-text">You're all caught up!</p>
                    <span className="notif-empty-sub">No new notifications at this time.</span>
                  </div>
                ) : (
                  notifications.map((item) => (
                    <div
                      key={item.id}
                      className={`notification-popover-item ${item.unread ? 'unread' : ''}`}
                      onClick={() => handleNotificationClick(item)}
                      role="button"
                      tabIndex={0}
                    >
                      <div className={`notification-item-avatar ${item.type}`}>
                        {item.type === 'status' && <Briefcase size={14} />}
                        {item.type === 'scheme' && <Sparkles size={14} />}
                        {item.type === 'doc' && <FileText size={14} />}
                        {item.type === 'alert' && <Clock size={14} />}
                      </div>
                      <div className="notification-item-text">
                        <div className="notification-item-top">
                          <span className="notif-item-title">{item.title}</span>
                          <span className="notif-item-time">{item.time}</span>
                        </div>
                        <p className="notif-item-message">{item.message}</p>
                      </div>
                      {item.unread && <span className="notif-item-dot" aria-hidden="true" />}
                    </div>
                  ))
                )}
              </div>

              <div className="notification-popover-footer">
                <button
                  type="button"
                  className="notif-footer-action-link"
                  onClick={() => {
                    setIsNotificationOpen(false);
                    navigate('/applications');
                  }}
                >
                  View All Applications
                </button>
                {notifications.length > 0 && (
                  <button
                    type="button"
                    className="notif-footer-clear-btn"
                    onClick={handleClearAllNotifications}
                  >
                    Clear all
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Short Profile Popover Wrapper */}
        <div className="header-profile-wrapper" ref={profileWrapperRef}>
          <button
            type="button"
            className={`user-profile-badge ${isProfileOpen ? 'active' : ''}`}
            onClick={toggleProfileMenu}
            aria-expanded={isProfileOpen}
            aria-label="User profile menu"
            title="Open Profile Menu"
          >
            <div className="user-avatar-hs" aria-hidden="true">
              {userInfo.avatarUrl ? (
                <img src={userInfo.avatarUrl} alt={userInfo.name} className="navbar-avatar-img" />
              ) : (
                userInfo.initials
              )}
            </div>
            <div className="user-info">
              <span className="user-name">{userInfo.name}</span>
              <span className="user-role">{userInfo.role}</span>
            </div>
            <ChevronDown
              size={14}
              className={`user-chevron ${isProfileOpen ? 'rotate' : ''}`}
              aria-hidden="true"
            />
          </button>

          {/* Short Profile Popover */}
          {isProfileOpen && (
            <div className="profile-popover" role="menu" aria-label="User profile menu">
              {/* Profile Card Header */}
              <div className="profile-popover-card">
                <div className="profile-popover-avatar-box">
                  {userInfo.avatarUrl ? (
                    <img
                      src={userInfo.avatarUrl}
                      alt={userInfo.fullName}
                      className="profile-popover-avatar-img"
                    />
                  ) : (
                    <div className="profile-popover-avatar-initials">{userInfo.initials}</div>
                  )}
                </div>
                <div className="profile-popover-user-meta">
                  <h3 className="profile-popover-user-name">{userInfo.fullName}</h3>
                  <span className="profile-popover-user-role">{userInfo.role}</span>
                  <span className="profile-popover-user-email">{userInfo.email}</span>
                  <span className="profile-popover-user-loc">{userInfo.state}, India</span>
                </div>
              </div>

              {/* Profile Completion Meter */}
              <div className="profile-popover-meter-box">
                <div className="popover-meter-labels">
                  <span className="popover-meter-title">Profile Strength</span>
                  <span className="popover-meter-val">75% Complete</span>
                </div>
                <div className="popover-meter-track">
                  <div className="popover-meter-fill" style={{ width: '75%' }} />
                </div>
              </div>

              {/* Navigation Items */}
              <div className="profile-popover-nav-list">
                <button
                  type="button"
                  className="profile-popover-nav-btn"
                  onClick={() => {
                    setIsProfileOpen(false);
                    navigate('/profile');
                  }}
                >
                  <User size={16} />
                  <span>View Full Profile</span>
                </button>
                <button
                  type="button"
                  className="profile-popover-nav-btn"
                  onClick={() => {
                    setIsProfileOpen(false);
                    navigate('/documents');
                  }}
                >
                  <FileText size={16} />
                  <span>My Documents & Locker</span>
                </button>
                <button
                  type="button"
                  className="profile-popover-nav-btn"
                  onClick={() => {
                    setIsProfileOpen(false);
                    navigate('/applications');
                  }}
                >
                  <Briefcase size={16} />
                  <span>Track Applications</span>
                </button>
                <button
                  type="button"
                  className="profile-popover-nav-btn"
                  onClick={() => {
                    setIsProfileOpen(false);
                    navigate('/profile');
                  }}
                >
                  <Shield size={16} />
                  <span>Security & Password</span>
                </button>
              </div>

              {/* Divider & Sign Out */}
              <div className="profile-popover-divider" />
              <button
                type="button"
                className="profile-popover-logout-btn"
                onClick={handleLogout}
              >
                <LogOut size={16} />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
