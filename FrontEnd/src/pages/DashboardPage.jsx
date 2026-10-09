import React, { useState, useEffect } from 'react';
import PageContainer from '../components/layout/PageContainer';
import HeroBanner from '../components/dashboard/HeroBanner';
import MetricCardsRow from '../components/dashboard/MetricCardsRow';
import TopOpportunitiesSection from '../components/dashboard/TopOpportunitiesSection';
import ProfileBanner from '../components/dashboard/ProfileBanner';
import { authenticatedFetch } from '../services/authService';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const [metrics, setMetrics] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await authenticatedFetch(`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/dashboard`);
      if (!res.ok) {
        throw new Error(`Dashboard request failed (${res.status})`);
      }
      const data = await res.json();
      if (data.success && data.data) {
        const d = data.data;

        // Map live metrics from BackEnd
        if (Array.isArray(d.metrics)) {
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

        // Map live top opportunities from BackEnd using canonical eligibility statuses
        if (Array.isArray(d.topOpportunities)) {
          setOpportunities(d.topOpportunities.map(o => {
            const status = String(o.eligibilityStatus || o.eligibility?.status || 'UNKNOWN').toUpperCase();
            const isPass = status === 'PASS' || o.isEligible === true;
            const isReview = status === 'REVIEW';
            const isFail = status === 'FAIL';

            let badgeLabel = 'Verification Needed';
            let badgeClass = 'badge-blue';
            let conditionType = 'warning';
            let conditionText = 'Criteria unverified';

            if (isPass) {
              badgeLabel = 'Eligible';
              badgeClass = 'badge-green';
              conditionType = 'success';
              conditionText = 'All conditions met';
            } else if (isReview) {
              badgeLabel = 'Review Required';
              badgeClass = 'badge-amber';
              conditionType = 'warning';
              conditionText = 'Document review required';
            } else if (isFail) {
              badgeLabel = 'Not Eligible';
              badgeClass = 'badge-neutral';
              conditionType = 'warning';
              conditionText = 'Criteria not met';
            }

            return {
              id: o.schemeId || o.id,
              name: o.schemeName || o.name,
              fullName: o.ministry || o.description || 'Government of India',
              tags: o.tags || ['Welfare Scheme', 'Central Sector'],
              estimatedBenefit: o.benefitDisplay || (o.benefitAmount ? `₹${Number(o.benefitAmount).toLocaleString('en-IN')}` : 'Financial Assistance'),
              conditionType,
              conditionText,
              matchRate: badgeLabel,
              matchBadgeClass: badgeClass,
              emblemType: String(o.schemeId || '').includes('msme') ? 'msme' : String(o.schemeId || '').includes('kisan') ? 'kisan' : 'ashoka'
            };
          }));
        }

        // Set live user profile
        if (d.user) {
          setUserProfile(d.user);
        }
      }
    } catch (err) {
      console.warn('Dashboard API error:', err.message);
      setError(err.message || 'Unable to connect to dashboard service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();

    const handleUserUpdate = () => {
      fetchDashboard();
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
      <div className="dashboard-layout">
        {/* Error notification banner if service is degraded */}
        {error && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: '#FEF3F2', border: '1px solid #FECDCA', borderRadius: '8px', color: '#B42318', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={18} />
              <span style={{ fontSize: '13.5px', fontWeight: 500 }}>{error}</span>
            </div>
            <button
              type="button"
              onClick={fetchDashboard}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'none', border: 'none', color: '#B42318', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}
            >
              <RefreshCw size={14} />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* 1. Hero Banner with Namaste greeting and India Gate visual */}
        <HeroBanner userProfile={userProfile} />

        {/* 2. Four key metric cards */}
        <MetricCardsRow metrics={metrics} />

        {/* 3. Top Opportunities for You cards & side widgets */}
        <TopOpportunitiesSection opportunities={opportunities} />

        {/* 4. Complete Your Profile callout banner */}
        <ProfileBanner profileCompleted={userProfile?.profileCompleted} />
      </div>
    </PageContainer>
  );
}
