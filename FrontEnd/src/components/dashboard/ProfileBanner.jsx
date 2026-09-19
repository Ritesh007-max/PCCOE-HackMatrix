import React from 'react';
import { Link } from 'react-router-dom';
import { Users, ArrowRight } from 'lucide-react';
import tajMahalBg from '../../assets/taj_mahal_bg.jpg';

export default function ProfileBanner() {
  return (
    <section className="complete-profile-banner" aria-label="Profile Completion Banner">
      {/* Subtle Taj Mahal architectural watermark */}
      <div
        className="banner-taj-silhouette"
        style={{ backgroundImage: `url(${tajMahalBg})` }}
        aria-hidden="true"
      />

      <div className="banner-left-wrap">
        <div className="banner-icon-circle" aria-hidden="true">
          <Users size={22} />
        </div>
        <div className="banner-text-col">
          <h3 className="banner-title-txt">
            Complete Your Profile for Better Recommendations
          </h3>
          <p className="banner-sub-txt">
            Help us understand your goals to show more relevant schemes.
          </p>
        </div>
      </div>

      <Link to="/profile" className="btn-update-profile-saffron">
        <span>Update Profile</span>
        <ArrowRight size={16} />
      </Link>
    </section>
  );
}
