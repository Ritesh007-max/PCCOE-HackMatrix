import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  FileText,
  Building2,
  ShieldCheck,
  Bookmark,
  Share2,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import PageContainer from '../components/layout/PageContainer';
import { SCHEMES } from '../data/schemesData';
import SchemeLogo from '../components/schemes/SchemeLogo';

export default function SchemeDetailsPage() {
  const { schemeId = 'pmegp' } = useParams();
  const [activeTab, setActiveTab] = useState('overview');

  const scheme = SCHEMES.find((s) => s.id === schemeId) || SCHEMES[0];

  return (
    <PageContainer>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Back Link Breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Link
            to="/discover"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontFamily: 'var(--font-sans)',
              fontSize: '13.5px',
              fontWeight: 500,
              color: '#005B50',
              textDecoration: 'none'
            }}
          >
            <ArrowLeft size={16} />
            <span>Back to Discover Schemes</span>
          </Link>
          <span style={{ color: '#98A2B3' }}>/</span>
          <span style={{ color: '#667085', fontSize: '13.5px' }}>{scheme.title}</span>
        </div>

        {/* Scheme Header Card */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #EAECF0',
            borderRadius: '12px',
            padding: '24px 28px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: '20px',
            flexWrap: 'wrap',
            boxShadow: '0 1px 3px rgba(16, 24, 40, 0.04)'
          }}
        >
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center', flex: 1, minWidth: '280px' }}>
            <div
              style={{
                width: '72px',
                height: '72px',
                borderRadius: '12px',
                backgroundColor: '#FAF8F5',
                border: '1px solid #EFECE6',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '8px',
                flexShrink: 0
              }}
            >
              <SchemeLogo scheme={scheme} />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: '28px', fontWeight: 700, color: '#10243A', margin: 0 }}>
                  {scheme.title}
                </h1>
                <span className={`scheme-match-badge match-${scheme.matchType || 'green'}`}>
                  {scheme.matchScore}% Match
                </span>
              </div>
              <h2 style={{ fontFamily: 'var(--font-sans)', fontSize: '15px', fontWeight: 500, color: '#475467', margin: 0 }}>
                {scheme.subtitle}
              </h2>
              {scheme.ministry && (
                <p style={{ fontFamily: 'var(--font-sans)', fontSize: '12.5px', color: '#667085', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Building2 size={14} />
                  <span>{scheme.ministry}</span>
                </p>
              )}
            </div>
          </div>

          {/* Benefit Badge & Apply Action */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '10px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '22px', fontWeight: 700, color: '#073B30' }}>
                {scheme.benefitAmount}
              </div>
              <div style={{ fontSize: '12px', color: '#667085' }}>
                {scheme.benefitSubtitle || 'Estimated Benefit'}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                onClick={() => alert(`Application initiated for ${scheme.title}! Our agent will guide your document submission.`)}
                className="btn-scheme-view primary"
                style={{ padding: '9px 20px' }}
              >
                <span>Apply for Scheme</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            borderBottom: '1px solid #EAECF0',
            paddingBottom: '2px'
          }}
        >
          {['overview', 'eligibility', 'benefits', 'documents'].map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: activeTab === tab ? '2.5px solid #073B30' : '2.5px solid transparent',
                padding: '10px 18px',
                fontFamily: 'var(--font-sans)',
                fontSize: '14.5px',
                fontWeight: activeTab === tab ? 600 : 500,
                color: activeTab === tab ? '#073B30' : '#667085',
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content Box */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #EAECF0',
            borderRadius: '12px',
            padding: '28px',
            boxShadow: '0 1px 3px rgba(16, 24, 40, 0.04)'
          }}
        >
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#10243A' }}>About the Scheme</h3>
              <p style={{ fontSize: '14.5px', lineHeight: 1.6, color: '#344054' }}>
                {scheme.overview || scheme.description}
              </p>
              <div style={{ marginTop: '8px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#10243A', marginBottom: '8px' }}>Categorization Tags</h4>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {scheme.tags.map((t) => (
                    <span key={t} className="scheme-card-tag-pill" style={{ fontSize: '13px', padding: '4px 10px' }}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'eligibility' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#10243A' }}>Who is Eligible?</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {(scheme.eligibilityCriteria || [
                  'Citizen of India with valid national identity credentials (Aadhaar / PAN)',
                  'Age criteria met within the recommended bracket',
                  'Income guidelines satisfy the scheme threshold limits',
                  'Possesses active bank account for DBT credits'
                ]).map((rule, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                    <ShieldCheck size={20} color="#073B30" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span style={{ fontSize: '14.5px', color: '#344054', lineHeight: 1.5 }}>{rule}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'benefits' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#10243A' }}>Scheme Benefits & Subsidies</h3>
              <div style={{ padding: '16px 20px', backgroundColor: '#F0FDF4', borderRadius: '8px', border: '1px solid #BBF7D0' }}>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#15803D' }}>
                  {scheme.benefitAmount}
                </div>
                <div style={{ fontSize: '13px', color: '#166534', marginTop: '4px' }}>
                  {scheme.benefitSubtitle || 'Direct Financial Assistance & Subsidized Support'}
                </div>
              </div>
              <p style={{ fontSize: '14.5px', lineHeight: 1.5, color: '#344054' }}>
                Beneficiaries receive disbursement directly through Public Financial Management System (PFMS) into their Aadhaar-seeded bank accounts without middlemen or administrative deduction.
              </p>
            </div>
          )}

          {activeTab === 'documents' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#10243A' }}>Documents Required for Application</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '12px' }}>
                {(scheme.documentsRequired || [
                  'Aadhaar Card (Identity & Address)',
                  'PAN Card',
                  'Bank Account Passbook / Cancelled Cheque',
                  'Income Certificate / Proof of Earnings',
                  'Passport Sized Photographs'
                ]).map((doc, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '12px 14px',
                      backgroundColor: '#FAF8F5',
                      border: '1px solid #EFECE6',
                      borderRadius: '8px'
                    }}
                  >
                    <FileText size={18} color="#005B50" />
                    <span style={{ fontSize: '13.5px', fontWeight: 500, color: '#10243A' }}>{doc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
}
