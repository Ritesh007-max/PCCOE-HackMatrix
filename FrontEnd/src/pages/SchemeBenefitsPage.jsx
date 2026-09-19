import React from 'react';
import { useParams, Link } from 'react-router-dom';
import PageContainer from '../components/layout/PageContainer';

export default function SchemeBenefitsPage() {
  const { schemeId = 'pmegp' } = useParams();

  return (
    <PageContainer>
      <div className="page-placeholder">
        <div className="page-placeholder-header">
          <h1 className="font-h1">Scheme Benefits</h1>
          <p className="font-body">Dedicated financial benefits breakdown, margin money subsidy, and calculator.</p>
        </div>
        <div className="page-placeholder-card">
          <div className="placeholder-badge-row">
            <span className="badge badge-success">Foundation Ready</span>
            <span className="badge badge-saffron">Route: /schemes/:schemeId/benefits</span>
            <span className="badge badge-blue">Scheme ID: {schemeId}</span>
          </div>
          <p className="font-body-large">
            Scheme Benefits detailed breakdown (Financial Hero Number, Subsidy Matrix Table, Supporting Cards) will be integrated in the subsequent implementation step.
          </p>
          <div style={{ marginTop: '12px' }}>
            <Link to={`/schemes/${schemeId}`} className="btn btn-outline">
              ← Back to Scheme Details
            </Link>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
