import React from 'react';
import { ShieldAlert, Clock, RefreshCw, LogOut, Lock } from 'lucide-react';
import '../../styles/sessionTimeout.css';

/**
 * Banking-Grade Session Inactivity Warning Modal
 * Displays a countdown timer when user inactivity approaches auto-logout threshold.
 */
export default function SessionTimeoutModal({
  isOpen,
  secondsRemaining,
  maxWarningSeconds = 60,
  onExtendSession,
  onLogout,
  isRefreshing = false,
}) {
  if (!isOpen) return null;

  const progressPercentage = Math.max(
    0,
    Math.min(100, (secondsRemaining / maxWarningSeconds) * 100)
  );

  return (
    <div
      className="session-timeout-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="sessionTimeoutTitle"
      aria-describedby="sessionTimeoutDesc"
    >
      <div className="session-timeout-card">
        {/* National Tricolor Stripe */}
        <div className="session-timeout-ribbon" aria-hidden="true" />

        <div className="session-timeout-body">
          {/* Security Shield Icon */}
          <div className="session-timeout-badge-wrap" aria-hidden="true">
            <ShieldAlert size={36} className="session-timeout-shield-icon" />
            <div className="session-timeout-clock-subicon">
              <Clock size={16} />
            </div>
          </div>

          <h2 id="sessionTimeoutTitle" className="session-timeout-title">
            Session Expiring Soon
          </h2>

          <p id="sessionTimeoutDesc" className="session-timeout-desc">
            For your security as per national digital financial standards, your session
            will automatically expire due to inactivity.
          </p>

          {/* Countdown Display */}
          <div className="session-timeout-counter-box">
            <div className="session-timeout-counter-label">
              Time Remaining
            </div>
            <div className="session-timeout-counter-value">
              {String(secondsRemaining).padStart(2, '0')}
              <span className="session-timeout-counter-unit">sec</span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="session-timeout-progressbar-wrap" aria-hidden="true">
            <div
              className="session-timeout-progressbar-fill"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>

          {/* Action Buttons */}
          <div className="session-timeout-actions">
            <button
              type="button"
              id="stayLoggedInBtn"
              className="session-btn-extend"
              onClick={onExtendSession}
              disabled={isRefreshing}
            >
              <RefreshCw
                size={16}
                className={isRefreshing ? 'animate-spin' : ''}
              />
              <span>{isRefreshing ? 'Renewing...' : 'Stay Logged In'}</span>
            </button>

            <button
              type="button"
              id="logoutNowBtn"
              className="session-btn-logout"
              onClick={onLogout}
            >
              <LogOut size={16} />
              <span>Log Out</span>
            </button>
          </div>

          {/* Footnote */}
          <div className="session-timeout-footer">
            <Lock size={12} />
            <span>FIN Secure Session Guard &bull; Government of India</span>
          </div>
        </div>
      </div>
    </div>
  );
}
