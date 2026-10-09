import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { TricolorRibbon } from '../common/BrandAssets';
import indiaGateHero from '../../assets/india_gate_hero.jpg';
import namaskaraImg from '../../assets/namaskara.png';
import { resolveDisplayName } from '../../services/authService';

export default function HeroBanner({ userProfile }) {
  const [userName, setUserName] = useState(() => {
    try {
      if (userProfile?.fullName && userProfile.fullName.toLowerCase() !== 'user') {
        return userProfile.fullName;
      }
      
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        const resolved = resolveDisplayName(parsed, parsed?.email);
        if (resolved && resolved.toLowerCase() !== 'user') return resolved;
      }
    } catch (e) {}
    return userProfile?.fullName || 'Citizen';
  });

  useEffect(() => {
    if (userProfile?.fullName && userProfile.fullName.toLowerCase() !== 'user') {
      setUserName(userProfile.fullName);
    }

    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || JSON.parse(localStorage.getItem('fin_user') || '{}');
        const resolved = resolveDisplayName(user, user?.email);
        if (resolved && resolved.toLowerCase() !== 'user') setUserName(resolved);
      } catch (err) {}
    };

    window.addEventListener('fin_user_updated', handleUserUpdate);
    window.addEventListener('storage', handleUserUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleUserUpdate);
      window.removeEventListener('storage', handleUserUpdate);
    };
  }, [userProfile]);

  // Extract only the first name for this specific greeting spot on the dashboard
  const firstName = (userName && userName.toLowerCase() !== 'user')
    ? userName.trim().split(/\s+/)[0]
    : (userProfile?.fullName ? userProfile.fullName.trim().split(/\s+/)[0] : 'Citizen');

  const currentDate = new Date().toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });

  return (
    <section className="dashboard-hero-card" aria-label="Welcome Banner">
      {/* Background panoramic India Gate visual */}
      <div
        className="hero-bg-visual"
        style={{ backgroundImage: `url(${indiaGateHero})` }}
        aria-hidden="true"
      />

      {/* Left editorial content */}
      <div className="hero-left-content">
        <span className="hero-date">{currentDate}</span>
        <h1 className="hero-main-greeting">
          <span>Namaste, {firstName}</span>
          <img
            src={namaskaraImg}
            alt="🙏"
            title="Namaste"
            className="hero-namaste-icon"
          />
        </h1>
        <p className="hero-hinglish-message">
          Sarkar ki yojanaon se, aapke sapno ko nayi pehchaan.
        </p>
        <p className="hero-english-message">
          Let's find the right government schemes for your goals.
        </p>

        <div className="hero-actions-row">
          <Link to="/discover" className="btn btn-primary" style={{ padding: '11px 22px' }}>
            <span>Explore Schemes</span>
            <ArrowRight size={16} />
          </Link>
          <Link to="/profile" className="btn btn-outline" style={{ padding: '11px 20px' }}>
            <span>Complete Your Profile</span>
          </Link>
        </div>
      </div>

      {/* Right editorial government quote */}
      <div className="hero-right-editorial">
        <blockquote className="hero-quote-text">
          “Empowered citizens build a stronger India.”
        </blockquote>
        <cite className="hero-quote-author">— Government of India</cite>
        <TricolorRibbon width={56} height={5} />
      </div>
    </section>
  );
}
