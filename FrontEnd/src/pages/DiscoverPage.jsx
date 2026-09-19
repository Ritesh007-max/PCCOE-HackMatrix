import React from 'react';
import PageContainer from '../components/layout/PageContainer';

export default function DiscoverPage() {
  return (
    <PageContainer>
      <div className="page-placeholder">
        <div className="page-placeholder-header">
          <h1 className="font-h1">Discover Government Schemes</h1>
          <p className="font-body">Search, filter, and discover verified financial policies across India.</p>
        </div>
        <div className="page-placeholder-card">
          <div className="placeholder-badge-row">
            <span className="badge badge-success">Foundation Ready</span>
            <span className="badge badge-saffron">Route: /discover</span>
          </div>
          <p className="font-body-large">
            Discover Schemes search and filter UI will be integrated in the subsequent implementation step.
          </p>
        </div>
      </div>
    </PageContainer>
  );
}
