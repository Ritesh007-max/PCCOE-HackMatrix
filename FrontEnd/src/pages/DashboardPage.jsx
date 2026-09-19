import React from 'react';
import PageContainer from '../components/layout/PageContainer';
import HeroBanner from '../components/dashboard/HeroBanner';
import MetricCardsRow from '../components/dashboard/MetricCardsRow';
import TopOpportunitiesSection from '../components/dashboard/TopOpportunitiesSection';
import ProfileBanner from '../components/dashboard/ProfileBanner';

export default function DashboardPage() {
  return (
    <PageContainer>
      <div className="dashboard-layout">
        {/* 1. Hero Banner with Namaste Hemang and India Gate visual */}
        <HeroBanner />

        {/* 2. Four key metric cards */}
        <MetricCardsRow />

        {/* 3. Top Opportunities for You cards & side widgets */}
        <TopOpportunitiesSection />

        {/* 4. Complete Your Profile callout banner */}
        <ProfileBanner />
      </div>
    </PageContainer>
  );
}
