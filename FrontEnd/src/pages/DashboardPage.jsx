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
        setLoading(true);
        const res = await authenticatedFetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/dashboard`);
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.data) {
            const d = data.data;
            
            // Transform metrics from backend format
            if (d.metrics) {
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
            
            // Transform opportunities from backend format
            if (d.topOpportunities) {
              setOpportunities(d.topOpportunities.map((o, idx) => {
                const emblemTypes = ['ashoka', 'msme', 'kisan'];
                const badgeClasses = ['badge-success', 'badge-blue', 'badge-saffron'];
                const conditionTypes = ['success', 'warning', 'lock'];
                return {
                  id: o.schemeId,
                  emblemType: emblemTypes[idx % 3],
                  name: o.schemeName.split(' ')[0],
                  fullName: o.schemeName,
                  tags: o.eligibility || [],
                  matchRate: `${o.matchScore}% Match`,
                  matchBadgeClass: badgeClasses[idx % 3],
                  estimatedBenefit: o.benefitAmount ? `₹ ${o.benefitAmount.toLocaleString()}` : 'N/A',
                  conditionText: o.eligibility?.join(', ') || 'Check eligibility',
                  conditionType: conditionTypes[idx % 3]
                };
              }));
            }
            
            // Set user profile for HeroBanner
            if (d.user) {
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
