import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  Search,
  FileText,
  Inbox,
  Sparkles,
  X,
  LayoutDashboard,
  ClipboardCheck
} from 'lucide-react';
import { FinLogoClear } from '../common/BrandAssets';
import tricolorRibbonOriginal from '../../assets/tricolor_ribbon_original.png';
import ashokStambhSvg from '../../assets/ashok_stambh_vector.svg';
import { getStoredRole } from '../../services/authService';

const citizenNavItems = [
  { name: 'Dashboard', path: '/dashboard', icon: Home },
  { name: 'Discover Schemes', path: '/discover', icon: Search },
  { name: 'Suggested Schemes', path: '/suggested-schemes', icon: Sparkles },
  { name: 'My Documents', path: '/documents', icon: FileText },
  { name: 'Applications', path: '/applications', icon: Inbox },
];

const reviewerNavItems = [
  { name: 'Reviewer Dashboard', path: '/reviewer/dashboard', icon: LayoutDashboard },
  { name: 'Discover Schemes', path: '/discover', icon: Search },
  { name: 'Review Applications', path: '/reviewer/applications', icon: ClipboardCheck },
];

export default function Sidebar({ isOpen, onClose }) {
  const [role, setRole] = useState(getStoredRole);

  useEffect(() => {
    const handleRoleUpdate = () => {
      setRole(getStoredRole());
    };
    window.addEventListener('fin_user_updated', handleRoleUpdate);
    window.addEventListener('storage', handleRoleUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleRoleUpdate);
      window.removeEventListener('storage', handleRoleUpdate);
    };
  }, []);

  const isReviewer = role === 'reviewer';
  const navItems = isReviewer ? reviewerNavItems : citizenNavItems;
  const homePath = isReviewer ? '/reviewer/dashboard' : '/dashboard';

  return (
    <>
      {/* Mobile Backdrop */}
      <div
        className={`sidebar-backdrop ${isOpen ? 'open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside className={`app-sidebar ${isOpen ? 'open' : ''}`} aria-label="Main Navigation">
        {/* Top Logo Section with Crisp FIN + Tricolor + Subtitle */}
        <div className="sidebar-top-section">
          <div className="sidebar-brand-wrapper">
            <NavLink
              to={homePath}
              onClick={onClose}
              className="sidebar-brand-link"
              title="FIN - Financial Policy Intelligence"
            >
              <FinLogoClear />
            </NavLink>

            {/* Close button on mobile */}
            <button
              type="button"
              className="menu-toggle-btn mobile-close-btn"
              onClick={onClose}
              aria-label="Close sidebar menu"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Navigation links matching screenshot */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) => `sidebar-nav-link ${isActive ? 'active' : ''}`}
              >
                {/* Left vertical green indicator bar for active item */}
                <span className="active-green-bar" aria-hidden="true" />
                <Icon size={20} className="sidebar-nav-icon" strokeWidth={2.2} />
                <span className="sidebar-nav-label">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Lower Editorial Quote + Bharat Visual - IDENTICAL ON EVERY PAGE */}
        <div className="sidebar-bottom-section">
          {/* Middle Editorial Quote with clean line-by-line alignment */}
          <div className="sidebar-quote-container">
            <p className="sidebar-quote-text">
              “Sabka Saath,<br />
              Sabka Vikas,<br />
              Sabka Vishwas,<br />
              Sabka Prayas”
            </p>
            <span className="sidebar-quote-author">— Government of India</span>
          </div>

          {/* Full width tricolor ribbon spanning the entire sidebar */}
          <img
            src={tricolorRibbonOriginal}
            alt=""
            className="sidebar-quote-ribbon-img"
            aria-hidden="true"
          />

          {/* Bottom Bharat Building Photo with editorial overlay */}
          <div
            className="sidebar-building-bottom-wrapper"
            role="img"
            aria-label="Bharat - Indian Government Architecture"
          >
            <div className="sidebar-building-overlay">
              <span className="sidebar-bharat-title">Bharat</span>
              <span className="sidebar-bharat-subtitle">for a brighter tomorrow.</span>
              <div className="sidebar-bharat-tricolor-line" aria-hidden="true" />
            </div>
          </div>

          {/* Bottom dark green bar segment matching footer bottom bar */}
          <div className="sidebar-bottom-bar-segment">
            <div className="sidebar-bottom-bar-content">
              <img
                src={ashokStambhSvg}
                alt="State Emblem of India"
                className="sidebar-bottom-bar-emblem"
                aria-hidden="true"
              />
              <span className="sidebar-bottom-bar-motto">सत्यमेव जयते</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
