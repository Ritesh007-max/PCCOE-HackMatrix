import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import SessionTimeoutModal from './SessionTimeoutModal';
import {
  refreshAuthToken,
  logoutUser,
  clearAuthSession,
  getStoredToken,
  getStoredRefreshToken,
} from '../../services/authService';

// Configurable session timeouts (default: 5 minutes idle timeout with 60 seconds warning)
// Can be overridden via VITE_SESSION_TIMEOUT_SEC and VITE_SESSION_WARNING_SEC in .env
const DEFAULT_TIMEOUT_SECONDS = 5 * 60; // 300 seconds (5 mins)
const DEFAULT_WARNING_SECONDS = 60; // 60 seconds warning window

const ENV_TIMEOUT_SEC = Number(import.meta.env.VITE_SESSION_TIMEOUT_SEC);
const ENV_WARNING_SEC = Number(import.meta.env.VITE_SESSION_WARNING_SEC);

const TOTAL_TIMEOUT_SEC = !isNaN(ENV_TIMEOUT_SEC) && ENV_TIMEOUT_SEC > 0
  ? ENV_TIMEOUT_SEC
  : DEFAULT_TIMEOUT_SECONDS;

const WARNING_DURATION_SEC = !isNaN(ENV_WARNING_SEC) && ENV_WARNING_SEC > 0
  ? Math.min(ENV_WARNING_SEC, TOTAL_TIMEOUT_SEC - 5)
  : DEFAULT_WARNING_SECONDS;

const STORAGE_KEY_LAST_ACTIVITY = 'fin_last_activity';

/**
 * SessionTimeoutManager
 * Monitors citizen user activity (mouse, keystrokes, touch, scroll) across all open tabs.
 * Warns citizen before session expires, seamlessly refreshes tokens when requested,
 * and securely logs out inactive citizens just like in high-security banking portals.
 *
 * KEY FIX: Uses isWarningOpenRef (a ref mirror of isWarningOpen state) so that
 * activity event handlers always read the CURRENT value — avoiding the stale
 * closure bug where mouse moves during the warning modal would incorrectly reset
 * the idle timer and dismiss the modal before the user can click a button.
 */
export default function SessionTimeoutManager() {
  const navigate = useNavigate();
  const [isWarningOpen, setIsWarningOpen] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(WARNING_DURATION_SEC);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const lastRecordedTimeRef = useRef(null);
  const throttleTimerRef = useRef(null);

  // *** THE FIX: ref mirror of isWarningOpen so event handlers always see the current value ***
  // Event handler closures capture the ref object (which is stable), not the stale state value.
  const isWarningOpenRef = useRef(false);

  // Keep the ref in sync with state every render
  useEffect(() => {
    isWarningOpenRef.current = isWarningOpen;
  }, [isWarningOpen]);

  // Helper to record activity both in memory and localStorage for multi-tab sync
  const recordActivity = useCallback(() => {
    const now = Date.now();
    lastRecordedTimeRef.current = now;

    // Throttle writing to localStorage to once every 3 seconds for optimal performance
    if (!throttleTimerRef.current) {
      throttleTimerRef.current = setTimeout(() => {
        try {
          localStorage.setItem(STORAGE_KEY_LAST_ACTIVITY, String(now));
        } catch {
          // Storage may be unavailable in privacy-restricted browser contexts.
        }
        throttleTimerRef.current = null;
      }, 3000);
    }
  }, []);

  // Perform logout and redirect to login page with inactivity reason
  const handleTimeoutLogout = useCallback(async () => {
    setIsWarningOpen(false);
    isWarningOpenRef.current = false;
    clearAuthSession();
    try {
      await logoutUser();
    } catch {
      // Storage may be unavailable in privacy-restricted browser contexts.
    }
    navigate('/login?reason=timeout', { replace: true });
  }, [navigate]);

  // Handle explicit manual logout from warning dialog
  const handleExplicitLogout = useCallback(async () => {
    setIsWarningOpen(false);
    isWarningOpenRef.current = false;
    clearAuthSession();
    try {
      await logoutUser();
    } catch {
      // Storage may be unavailable in privacy-restricted browser contexts.
    }
    navigate('/login', { replace: true });
  }, [navigate]);

  // Handle citizen clicking "Stay Logged In"
  const handleExtendSession = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const refreshToken = getStoredRefreshToken();
      if (refreshToken) {
        await refreshAuthToken();
      }
    } catch (err) {
      console.warn('Silent token renewal encountered error:', err);
    } finally {
      setIsRefreshing(false);
      setIsWarningOpen(false);
      isWarningOpenRef.current = false;
      setSecondsRemaining(WARNING_DURATION_SEC);
      const now = Date.now();
      lastRecordedTimeRef.current = now;
      try {
        localStorage.setItem(STORAGE_KEY_LAST_ACTIVITY, String(now));
      } catch {
        // Storage may be unavailable in privacy-restricted browser contexts.
      }
    }
  }, []);

  // Setup DOM interaction listeners to detect user activity.
  // Registered ONCE on mount — no dependency on isWarningOpen state,
  // so the handler is NEVER torn down and re-registered while the modal is showing.
  useEffect(() => {
    if (!getStoredToken()) return;

    // Initialize activity timestamp
    const now = Date.now();
    lastRecordedTimeRef.current = now;
    if (!localStorage.getItem(STORAGE_KEY_LAST_ACTIVITY)) {
      try {
        localStorage.setItem(STORAGE_KEY_LAST_ACTIVITY, String(now));
      } catch {
        // Storage may be unavailable in privacy-restricted browser contexts.
      }
    }

    const activityEvents = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'];

    const handleUserInteraction = () => {
      // Read from isWarningOpenRef — always current, never stale.
      // When the warning modal is visible the user must explicitly click
      // "Stay Logged In" or "Log Out"; hovering/scrolling does nothing.
      if (!isWarningOpenRef.current) {
        recordActivity();
      }
    };

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleUserInteraction, { passive: true });
    });

    // Cross-tab synchronization via storage event
    const handleStorageChange = (e) => {
      if (e.key === STORAGE_KEY_LAST_ACTIVITY && e.newValue) {
        const remoteTime = Number(e.newValue);
        if (!isNaN(remoteTime)) {
          lastRecordedTimeRef.current = Math.max(lastRecordedTimeRef.current, remoteTime);
          // If another tab was active, close the warning dialog here too
          if (isWarningOpenRef.current) {
            setIsWarningOpen(false);
            isWarningOpenRef.current = false;
            setSecondsRemaining(WARNING_DURATION_SEC);
          }
        }
      } else if (e.key === 'fin_token' && !e.newValue) {
        // Logged out in another tab — redirect immediately
        navigate('/login', { replace: true });
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleUserInteraction);
      });
      window.removeEventListener('storage', handleStorageChange);
      if (throttleTimerRef.current) clearTimeout(throttleTimerRef.current);
    };
  }, [recordActivity, navigate]); // intentionally omit isWarningOpen — ref is used instead

  // Main Interval Timer — ticks every second to check idle time
  useEffect(() => {
    if (!getStoredToken()) return;

    const intervalId = setInterval(() => {
      const now = Date.now();

      const storedLastStr = localStorage.getItem(STORAGE_KEY_LAST_ACTIVITY);
      const storedLast = storedLastStr ? Number(storedLastStr) : lastRecordedTimeRef.current;
      const effectiveLastActivity = Math.max(lastRecordedTimeRef.current, isNaN(storedLast) ? 0 : storedLast);

      const idleSeconds = Math.floor((now - effectiveLastActivity) / 1000);
      const remainingSeconds = TOTAL_TIMEOUT_SEC - idleSeconds;

      if (remainingSeconds <= 0) {
        // Inactivity timeout reached — force logout
        handleTimeoutLogout();
      } else if (remainingSeconds <= WARNING_DURATION_SEC) {
        // Within warning window — show/update modal
        setSecondsRemaining(remainingSeconds);
        setIsWarningOpen(true);
      } else {
        // Still plenty of time — ensure modal is closed
        setIsWarningOpen(false);
      }
    }, 1000);

    return () => clearInterval(intervalId);
  }, [handleTimeoutLogout]);

  return (
    <SessionTimeoutModal
      isOpen={isWarningOpen}
      secondsRemaining={secondsRemaining}
      maxWarningSeconds={WARNING_DURATION_SEC}
      onExtendSession={handleExtendSession}
      onLogout={handleExplicitLogout}
      isRefreshing={isRefreshing}
    />
  );
}
