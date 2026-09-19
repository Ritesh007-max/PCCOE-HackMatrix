import React from 'react';
import { useParams, Link } from 'react-router-dom';
import PageContainer from '../components/layout/PageContainer';

export default function SchemeDetailsPage() {
  const { schemeId = 'pmegp' } = useParams();

  return (
    <PageContainer>
      <div className="page-placeholder">
        <div className="page-placeholder-header">
          <h1 className="font-h1">Scheme Details</h1>
          <p className="font-body">Detailed overview, eligibility rules, guidelines, and application steps.</p>
        </div>
        <div className="page-placeholder-card">
          <div className="placeholder-badge-row">
            <span className="badge badge-success">Foundation Ready</span>
            <span className="badge badge-saffron">Route: /schemes/:schemeId</span>
            <span className="badge badge-blue">Scheme ID: {schemeId}</span>
          </div>
          <p className="font-body-large">
            Scheme Details view with 6-tab system (Overview, Eligibility, Benefits, Documents, How to Apply, Source & Rules) will be integrated in the subsequent implementation step.
          </p>
          <div style={{ marginTop: '12px' }}>
            <Link to={`/schemes/${schemeId}/benefits`} className="btn btn-secondary">
              View Scheme Benefits Deep Dive →
            </Link>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
