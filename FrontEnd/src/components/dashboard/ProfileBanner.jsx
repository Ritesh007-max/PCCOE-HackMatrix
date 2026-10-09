import React from 'react';
import { Link } from 'react-router-dom';
import { Users, ArrowRight } from 'lucide-react';

export default function ProfileBanner({ profileCompleted = 0 }) {
  const isComplete = Number(profileCompleted) >= 100;

  return (
    <section className="complete-profile-banner" aria-label="Profile Completion Banner">
      <div className="banner-left-wrap">
        <div className="banner-icon-circle" aria-hidden="true">
          <Users size={22} />
        </div>
        <div className="banner-text-col">
          <h3 className="banner-title-txt">
            {isComplete ? 'Your Profile is 100% Complete' : 'Complete Your Profile for Better Recommendations'}
          </h3>
          <p className="banner-sub-txt">
            {isComplete
              ? 'Your personal details are up to date for personalized schemes and eligibility matching.'
              : 'Help us understand your goals to show more relevant schemes.'}
          </p>
        </div>
      </div>

      <Link to="/profile" className="btn-update-profile-saffron">
        <span>{isComplete ? 'View Profile' : 'Update Profile'}</span>
        <ArrowRight size={16} />
      </Link>
    </section>
  );
}
