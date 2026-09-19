import React from 'react';
import { Link } from 'react-router-dom';
import PageContainer from '../components/layout/PageContainer';

export default function NotFoundPage() {
  return (
    <PageContainer>
      <div className="page-placeholder">
        <div className="page-placeholder-card" style={{ textAlign: 'center', alignItems: 'center' }}>
          <h1 className="font-h1" style={{ color: 'var(--color-error)' }}>404</h1>
          <h2 className="font-h2">Page Not Found</h2>
          <p className="font-body">
            The requested policy page or route does not exist.
          </p>
          <div style={{ marginTop: '16px' }}>
            <Link to="/dashboard" className="btn btn-primary">
              Return to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </PageContainer>
  );
}
