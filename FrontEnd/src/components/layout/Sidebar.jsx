import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  Search,
  FileText,
  Inbox,
  User,
  X
} from 'lucide-react';
import finLogoOriginal from '../../assets/fin_logo_original.png';
import sidebarBuildingOriginal from '../../assets/sidebar_building_original.png';
import tricolorRibbonOriginal from '../../assets/tricolor_ribbon_original.png';

const navItems = [
  { name: 'Dashboard', path: '/dashboard', icon: Home },
  { name: 'Discover Schemes', path: '/discover', icon: Search },
  { name: 'My Documents', path: '/documents', icon: FileText },
  { name: 'Applications', path: '/applications', icon: Inbox },
  { name: 'Profile', path: '/profile', icon: User },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {/* Mobile Backdrop */}
      <div
        className={`sidebar-backdrop ${isOpen ? 'open' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside className={`app-sidebar ${isOpen ? 'open' : ''}`} aria-label="Main Navigation">
        {/* Top Logo Section with Original FIN + Tricolor + Subtitle */}
        <div className="sidebar-top-section">
          <div className="sidebar-brand-wrapper">
            <NavLink to="/dashboard" onClick={onClose} className="brand-image-link">
              <img
                src={finLogoOriginal}
                alt="FIN - Financial Policy Intelligence"
                className="sidebar-fin-brand-img"
              />
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

        {/* Lower Editorial Quote + Bharat Visual with 40-55px gap from navigation */}
        <div className="sidebar-bottom-section">
          {/* Middle Editorial Quote matching exact 5 lines */}
          <div className="sidebar-quote-container">
            <p className="sidebar-quote-text">
              “Sabka<br />
              Saath<br />
              Sabka Vikas<br />
              Sabka Vishwas<br />
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

          {/* Bottom Exact Bharat Building Photo (centered, 15-20% smaller) */}
          <div className="sidebar-building-bottom-wrapper">
            <img
              src={sidebarBuildingOriginal}
              alt="Bharat - for a brighter tomorrow."
              className="sidebar-building-img"
            />
          </div>
        </div>
      </aside>
    </>
  );
}
