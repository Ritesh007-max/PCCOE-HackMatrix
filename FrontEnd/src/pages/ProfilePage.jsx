import React from 'react';
import PageContainer from '../components/layout/PageContainer';

export default function ProfilePage() {
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
            <span className="badge badge-blue">Applicant: Hemang</span>
          </div>
          <p className="font-body-large">
            Applicant profile settings, income tier criteria, category verification, and location preferences will be integrated in the subsequent implementation step.
          </p>
        </div>
      </div>
    </PageContainer>
  );
}
