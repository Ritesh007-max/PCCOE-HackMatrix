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
import { FinLogoClear } from '../common/BrandAssets';
import sidebarBuildingClean from '../../assets/sidebar_building_clean.jpg';
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
        {/* Top Logo Section with Crisp FIN + Tricolor + Subtitle */}
        <div className="sidebar-top-section">
          <div className="sidebar-brand-wrapper">
            <NavLink
              to="/dashboard"
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

        {/* Lower Editorial Quote + Bharat Visual with 40-55px gap from navigation */}
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
          <div className="sidebar-building-bottom-wrapper">
            <img
              src={sidebarBuildingClean}
              alt="Bharat - Indian Government Architecture"
              className="sidebar-building-img"
            />
            <div className="sidebar-building-overlay">
              <span className="sidebar-bharat-title">Bharat</span>
              <span className="sidebar-bharat-subtitle">for a brighter tomorrow.</span>
              <div className="sidebar-bharat-tricolor-line" aria-hidden="true" />
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
