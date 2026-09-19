import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { TricolorRibbon } from '../common/BrandAssets';
import indiaGateHero from '../../assets/india_gate_hero.jpg';
import namaskaraImg from '../../assets/namaskara.png';

export default function HeroBanner() {
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
        <span className="hero-date">Thu, 18 Sep 2026</span>
        <h1 className="hero-main-greeting">
          <span>Namaste, UserName</span>
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
