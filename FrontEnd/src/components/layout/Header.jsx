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
import { resolveDisplayName, logoutUser, getStoredRole } from '../../services/authService';
import { searchSchemes } from '../../services/schemeService';
import { fetchUserApplications } from '../../services/applicationService';
import {
  fetchNotifications,
  markNotificationAsRead,
  markAllNotificationsAsRead
} from '../../services/notificationService';

function calculateProfileStrength(data) {
  if (!data) return 0;
  const fields = [
    data.fullName || data.name,
    data.email,
    data.phone,
    data.state,
    data.district || data.city,
    data.occupation,
    data.income || data.annual_income,
    data.applicantType,
    data.dob || data.date_of_birth,
    data.gender,
  ];
  const filledCount = fields.filter((val) => val && String(val).trim() !== '' && String(val).trim() !== 'Not added').length;
  return Math.round((filledCount / fields.length) * 100);
}

export default function Header({ onToggleSidebar, onToggleChat, onOpenChat, isChatOpen }) {
  const navigate = useNavigate();
  const handleChatClick = (e) => {
    if (typeof onToggleChat === 'function') {
      onToggleChat(e);
    } else if (typeof onOpenChat === 'function') {
      onOpenChat(e);
    } else {
      window.dispatchEvent(new CustomEvent('open_fin_chat'));
    }
  };
  // User State
  const [userInfo, setUserInfo] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        const resolved = resolveDisplayName(parsed, parsed?.email);
        const fullName = (resolved || parsed?.fullName || parsed?.name || 'Citizen').trim();
        const parts = fullName.split(' ').filter(Boolean);
        const initials = fullName.length >= 2 ? fullName.substring(0, 2).toUpperCase() : (fullName ? fullName.toUpperCase() : 'CI');
        const name = parts[0] || fullName;
        const avatarUrl = parsed?.avatarUrl || parsed?.avatar_url || '';
        const role = parsed?.applicantType ? `${parsed.applicantType} Applicant` : 'Individual Applicant';
        const email = parsed?.email || '';
        const state = parsed?.state || '';
        const strength = calculateProfileStrength(parsed);
        return { name, fullName, initials, avatarUrl, role, email, state, strength };
      }
    } catch (_) {}
    return {
      name: 'Citizen',
      fullName: 'Citizen',
      initials: 'CI',
      avatarUrl: '',
      role: 'Individual Applicant',
      email: '',
      state: '',
      strength: 0,
    };
  });

  const displayAvatar = userInfo.avatarUrl;
  const displayEmail = userInfo.email;
  const displayFullName = userInfo.fullName;
  const displayName = userInfo.name;

  // Dropdown States
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [notifications, setNotifications] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_notifications');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) return parsed;
      }
    } catch (_) {}
    return [];
  });

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

  // Synchronize notifications with real backend notification API
  useEffect(() => {
    let isMounted = true;
    const loadUserNotifications = () => {
      fetchNotifications()
        .then((res) => {
          if (isMounted && res && Array.isArray(res.notifications)) {
            setNotifications(res.notifications);
          }
        })
        .catch(() => {
          // Graceful fallback to application records if notifications endpoint is pending
          fetchUserApplications()
            .then((apps) => {
              if (isMounted && Array.isArray(apps) && apps.length > 0) {
                const appNotifs = apps.slice(0, 5).map((app, idx) => ({
                  id: `notif-app-${app.id || idx}`,
                  applicationId: app.id,
                  title: `Application ${app.status === 'approved' ? 'Approved' : app.status === 'action_required' ? 'Action Required' : app.status === 'rejected' ? 'Rejected' : 'Status Updated'}`,
                  message: `Your application for ${app.scheme_name || (app.scheme && app.scheme.name) || 'Scheme'} is currently ${app.status ? app.status.replace(/_/g, ' ') : 'Under Review'}.${app.remarks ? ` Note: "${app.remarks}"` : ''}`,
                  time: app.submitted_at || app.created_at ? new Date(app.submitted_at || app.created_at).toLocaleDateString('en-GB') : 'Recent',
                  unread: app.status === 'action_required' || idx === 0,
                  read: !(app.status === 'action_required' || idx === 0),
                  type: app.status === 'approved' ? 'doc' : 'status',
                  link: `/applications?open=${app.id}`
                }));
                setNotifications(appNotifs);
              }
            })
            .catch(() => {});
        });
    };

    loadUserNotifications();
    const interval = setInterval(loadUserNotifications, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Synchronize user updates
  useEffect(() => {
    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || JSON.parse(localStorage.getItem('fin_user') || '{}');
        const resolved = resolveDisplayName(user, user?.email);
        const fullName = (resolved || user?.fullName || user?.name || 'Citizen').trim();
        const parts = fullName.split(' ').filter(Boolean);
        const initials = fullName.length >= 2 ? fullName.substring(0, 2).toUpperCase() : (fullName ? fullName.toUpperCase() : 'CI');
        const name = parts[0] || fullName;
        const avatarUrl = user?.avatarUrl || user?.avatar_url || '';
        const role = user?.applicantType ? `${user.applicantType} Applicant` : 'Individual Applicant';
        const email = user?.email || '';
        const state = user?.state || '';
        const strength = calculateProfileStrength(user);
        setUserInfo({ name, fullName, initials, avatarUrl, role, email, state, strength });
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

  // Dynamic matching schemes based on query
  const [matchingSchemes, setMatchingSchemes] = useState([]);

  useEffect(() => {
    const q = searchQuery.trim();
    if (!q) {
      setMatchingSchemes([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await searchSchemes({ query: q, limit: 5 });
        const adapted = (res.schemes || []).map((s) => ({
          id: s.id,
          title: s.name || s.title,
          subtitle: s.ministry || s.subtitle || 'Government Scheme',
          description: s.benefit_summary || s.description || '',
          tags: s.tags || []
        }));
        setMatchingSchemes(adapted);
      } catch (_) {
        setMatchingSchemes([]);
      }
    }, 200);

    return () => clearTimeout(timer);
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
    markAllNotificationsAsRead().catch(() => {});
    setNotifications((prev) => prev.map((item) => ({ ...item, unread: false, read: true })));
  };

  const handleClearAllNotifications = () => {
    markAllNotificationsAsRead().catch(() => {});
    setNotifications([]);
  };

  const handleNotificationClick = (item) => {
    if (item.id && !item.id.startsWith('notif-app-')) {
      markNotificationAsRead(item.id).catch(() => {});
    }
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, unread: false, read: true } : n))
    );
    setIsNotificationOpen(false);

    const currentRole = getStoredRole();
    if (item.applicationId) {
      if (currentRole === 'reviewer') {
        navigate(`/reviewer/applications?open=${item.applicationId}`);
      } else {
        navigate(`/applications?open=${item.applicationId}`);
      }
    } else if (item.link) {
      navigate(item.link);
    } else {
      navigate(currentRole === 'reviewer' ? '/reviewer/applications' : '/applications');
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
    } catch (_) {
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
          onClick={handleChatClick}
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
              {displayAvatar ? (
                <img src={displayAvatar} alt={displayName} className="navbar-avatar-img" />
              ) : (
                userInfo.initials
              )}
            </div>
            <div className="user-info">
              <span className="user-name">{displayName}</span>
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
                  {displayAvatar ? (
                    <img
                      src={displayAvatar}
                      alt={displayFullName}
                      className="profile-popover-avatar-img"
                    />
                  ) : (
                    <div className="profile-popover-avatar-initials">{userInfo.initials}</div>
                  )}
                </div>
                <div className="profile-popover-user-meta">
                  <h3 className="profile-popover-user-name">{displayFullName}</h3>
                  <span className="profile-popover-user-role">{userInfo.role}</span>
                  <span className="profile-popover-user-email">{displayEmail}</span>
                  <span className="profile-popover-user-loc">{userInfo.state ? `${userInfo.state}, India` : 'India'}</span>
                </div>
              </div>

              {/* Profile Completion Meter */}
              <div className="profile-popover-meter-box">
                <div className="popover-meter-labels">
                  <span className="popover-meter-title">Profile Strength</span>
                  <span className="popover-meter-val">{userInfo.strength}% Complete</span>
                </div>
                <div className="popover-meter-track">
                  <div className="popover-meter-fill" style={{ width: `${userInfo.strength}%` }} />
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
