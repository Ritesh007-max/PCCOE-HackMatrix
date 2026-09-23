import React, { useState, useEffect } from 'react';
import PageContainer from '../components/layout/PageContainer';
import { resolveDisplayName } from '../services/authService';

export default function ProfilePage() {
  const [applicantName, setApplicantName] = useState(() => {
    try {
      const stored = localStorage.getItem('fin_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        const resolved = resolveDisplayName(parsed, parsed?.email);
        if (resolved) return resolved;
      }
    } catch (e) {}
    return 'Hemang';
  });

  useEffect(() => {
    const handleUserUpdate = (e) => {
      try {
        const user = e?.detail || JSON.parse(localStorage.getItem('fin_user') || '{}');
        const resolved = resolveDisplayName(user, user?.email);
        if (resolved) setApplicantName(resolved);
      } catch (err) {}
    };

    window.addEventListener('fin_user_updated', handleUserUpdate);
    window.addEventListener('storage', handleUserUpdate);
    return () => {
      window.removeEventListener('fin_user_updated', handleUserUpdate);
      window.removeEventListener('storage', handleUserUpdate);
    };
  }, []);

  return (
    <PageContainer>
      <div className="page-placeholder">
        <div className="page-placeholder-header">
          <h1 className="font-h1">Applicant Profile</h1>
          <p className="font-body">Personal demographic, business category, location, and income profile.</p>
        </div>
        <div className="page-placeholder-card">
          <div className="placeholder-badge-row">
            <span className="badge badge-success">Foundation Ready</span>
            <span className="badge badge-saffron">Route: /profile</span>
            <span className="badge badge-blue">Applicant: {applicantName}</span>
          </div>
          <p className="font-body-large">
            Applicant profile settings, income tier criteria, category verification, and location preferences will be integrated in the subsequent implementation step.
          </p>
        </div>
      </div>
    </PageContainer>
  );
}
