import React, { useState, useEffect } from 'react';
import PageContainer from '../components/layout/PageContainer';
import HeroBanner from '../components/dashboard/HeroBanner';
import MetricCardsRow from '../components/dashboard/MetricCardsRow';
import TopOpportunitiesSection from '../components/dashboard/TopOpportunitiesSection';
import ProfileBanner from '../components/dashboard/ProfileBanner';
import { authenticatedFetch } from '../services/authService';
import { dashboardMetrics as defaultMetrics, topOpportunities as defaultOpportunities } from '../data/dashboardData';

export default function DashboardPage() {
  const [metrics, setMetrics] = useState(defaultMetrics);
  const [opportunities, setOpportunities] = useState(defaultOpportunities);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const apiBase = (import.meta.env.VITE_API_URL || 'https://pccoe-hackmatrix-backend.onrender.com').replace(/\/+$/, '');
        const res = await authenticatedFetch(`${apiBase}/api/dashboard`);
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.data) {
            const d = data.data;
            
            // Only update metrics if valid non-empty data is provided
            if (d.metrics && d.metrics.some(m => {
              const val = parseInt(m.value) || 0;
              return val > 0;
            })) {
              setMetrics(d.metrics.map(m => ({
                id: m.key,
                value: m.value,
                title: m.label,
                subtitle: m.subtitle,
                colorType: m.icon === 'scheme' ? 'green' : m.icon === 'rupee' ? 'blue' : m.icon === 'document' ? 'amber' : 'purple',
                path: m.key === 'schemes' ? '/discover' : m.key === 'benefits' ? '/discover' : m.key === 'documents' ? '/documents' : '/applications',
                isWarning: m.isWarning
              })));
            }
            
            // Keep canonical top opportunities as shown in Image 1
            setOpportunities(defaultOpportunities);
            
            // Set user profile for HeroBanner if valid name and not generic 'User'
            if (d.user && d.user.fullName && d.user.fullName !== 'User') {
              setUserProfile(d.user);
            }
          }
        }
      } catch (err) {
        console.warn('Dashboard API failed, using fallback data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  return (
    <PageContainer>
      <div className="dashboard-layout">
        {/* 1. Hero Banner with Namaste Hemang and India Gate visual */}
        <HeroBanner userProfile={userProfile} />

        {/* 2. Four key metric cards */}
        <MetricCardsRow metrics={metrics} />

        {/* 3. Top Opportunities for You cards & side widgets */}
        <TopOpportunitiesSection opportunities={opportunities} />

        {/* 4. Complete Your Profile callout banner */}
        <ProfileBanner />
      </div>
    </PageContainer>
  );
}
