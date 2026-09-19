import React from 'react';

export default function PageContainer({ children, className = '' }) {
  return (
    <main className={`page-container ${className}`}>
      {children}
    </main>
  );
}
