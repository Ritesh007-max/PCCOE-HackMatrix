import React from 'react';
import { StandUpIndiaLogo, MudraLogo } from '../common/BrandAssets';

import ashokStambhOriginal from '../../assets/ashok_stambh_original.png';
import msmeOriginal from '../../assets/msme_original.png';
import kisanOriginal from '../../assets/kisan_original.png';

import pmSvanidhiImg from '../../assets/schemes/pm_svanidhi.jpg';
import startupIndiaImg from '../../assets/schemes/startup_india.jpg';
import skillIndiaImg from '../../assets/schemes/skill_india.jpg';
import pmFasalBimaImg from '../../assets/schemes/pm_fasal_bima.jpg';
import sukanyaSamriddhiImg from '../../assets/schemes/sukanya_samriddhi.jpg';
import ayushmanBharatImg from '../../assets/schemes/ayushman_bharat.jpg';
import pmAwasImg from '../../assets/schemes/pm_awas.jpg';
import pmVishwakarmaImg from '../../assets/schemes/pm_vishwakarma.jpg';

export default function SchemeLogo({ scheme, size = 64 }) {
  if (!scheme) return null;

  // 1. Direct photo / high-res official emblem matches
  if (scheme.id === 'pmegp') {
    return (
      <img
        src={ashokStambhOriginal}
        alt="State Emblem of India"
        className="scheme-card-logo-img"
        style={{ width: '42px', height: '52px', objectFit: 'contain' }}
      />
    );
  }

  if (scheme.id === 'msme-financial-support') {
    return (
      <img
        src={msmeOriginal}
        alt="MSME Government of India"
        className="scheme-card-logo-img"
        style={{ width: '54px', height: '38px', objectFit: 'contain' }}
      />
    );
  }

  if (scheme.id === 'pm-kisan') {
    return (
      <img
        src={kisanOriginal}
        alt="PM Kisan Samman Nidhi"
        className="scheme-card-logo-img"
        style={{ width: '44px', height: '44px', objectFit: 'contain' }}
      />
    );
  }

  if (scheme.id === 'stand-up-india' || scheme.logoType === 'standup') {
    return <StandUpIndiaLogo width={66} height={26} />;
  }

  if (scheme.id === 'mudra-yojana' || scheme.logoType === 'mudra') {
    return <MudraLogo size={42} />;
  }

  if (scheme.id === 'pm-svanidhi') {
    return (
      <img
        src={pmSvanidhiImg}
        alt="PM SVANidhi"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'startup-india-seed-fund') {
    return (
      <img
        src={startupIndiaImg}
        alt="Startup India"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'pmkvy-4' || scheme.id === 'naps-apprenticeship') {
    return (
      <img
        src={skillIndiaImg}
        alt="Skill India"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'pm-fasal-bima') {
    return (
      <img
        src={pmFasalBimaImg}
        alt="PM Fasal Bima Yojana"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'sukanya-samriddhi') {
    return (
      <img
        src={sukanyaSamriddhiImg}
        alt="Sukanya Samriddhi Yojana"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'ayushman-bharat') {
    return (
      <img
        src={ayushmanBharatImg}
        alt="Ayushman Bharat PM-JAY"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'pm-awas-yojana') {
    return (
      <img
        src={pmAwasImg}
        alt="Pradhan Mantri Awas Yojana"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  if (scheme.id === 'pm-vishwakarma') {
    return (
      <img
        src={pmVishwakarmaImg}
        alt="PM Vishwakarma Kaushal Samman"
        className="scheme-card-logo-img"
        style={{ width: '56px', height: '56px', objectFit: 'contain', borderRadius: '8px' }}
      />
    );
  }

  // 2. Kisan Credit Card (Golden chip & grain)
  if (scheme.id === 'kisan-credit-card') {
    return (
      <svg width="50" height="38" viewBox="0 0 60 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="56" height="40" rx="6" fill="#087443" stroke="#044D2C" strokeWidth="1.5" />
        <rect x="8" y="10" width="12" height="10" rx="2" fill="#FBBF24" stroke="#D97706" strokeWidth="1" />
        <path d="M40 8C35 12 34 24 40 32C45 24 46 12 40 8Z" fill="#FDE68A" />
        <text x="8" y="34" fill="#FFFFFF" fontSize="7" fontWeight="bold" fontFamily="sans-serif">KCC CARD</text>
      </svg>
    );
  }

  // 3. Education / Scholarships (Graduation cap & open book)
  if (scheme.categories?.includes('education')) {
    return (
      <svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="22" fill="#EEF4FF" stroke="#C7D7FE" strokeWidth="1" />
        {/* Mortarboard Cap */}
        <path d="M24 10L38 17L24 24L10 17L24 10Z" fill="#1D2939" />
        <path d="M15 20V27C15 31.5 24 35 24 35C24 35 33 31.5 33 27V20" stroke="#1D2939" strokeWidth="2.2" strokeLinecap="round" />
        {/* Golden Tassel */}
        <path d="M34 19V29" stroke="#E98A00" strokeWidth="2" strokeLinecap="round" />
        <circle cx="34" cy="30" r="2" fill="#E98A00" />
      </svg>
    );
  }

  // 4. Health & Medicine (PM Jan Aushadhi / Suraksha Bima / Jeevan Jyoti)
  if (scheme.categories?.includes('health')) {
    return (
      <svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="22" fill="#ECFDF3" stroke="#A6F4C5" strokeWidth="1" />
        <rect x="20" y="11" width="8" height="26" rx="3" fill="#087443" />
        <rect x="11" y="20" width="26" height="8" rx="3" fill="#087443" />
        <circle cx="24" cy="24" r="3" fill="#FFFFFF" />
      </svg>
    );
  }

  // 5. Tax Benefits / Financial Deductions / NPS / SGB (Rupee shield & growth)
  if (scheme.categories?.includes('tax-benefits')) {
    return (
      <svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="22" fill="#FEF6EC" stroke="#FADBB0" strokeWidth="1" />
        <path d="M24 8L36 13V23C36 30 24 38 24 38C24 38 12 30 12 23V13L24 8Z" fill="#E98A00" />
        <text x="24" y="27" textAnchor="middle" fill="#FFFFFF" fontSize="16" fontWeight="bold" fontFamily="sans-serif">₹</text>
      </svg>
    );
  }

  // 6. Women Empowerment (Mahila Samman, Matru Vandana, STEP)
  if (scheme.categories?.includes('women')) {
    return (
      <svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="22" fill="#FDF2F8" stroke="#FCE7F3" strokeWidth="1" />
        <circle cx="24" cy="17" r="7" stroke="#BE185D" strokeWidth="2.5" fill="none" />
        <path d="M24 24V37M19 31H29" stroke="#BE185D" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M12 24C16 18 32 18 36 24" stroke="#FB7185" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  }

  // 7. Agriculture (Krishi Sinchayee, Paramparagat, SMAM, Soil Health)
  if (scheme.categories?.includes('agriculture')) {
    return (
      <img
        src={kisanOriginal}
        alt="Agriculture"
        className="scheme-card-logo-img"
        style={{ width: '44px', height: '44px', objectFit: 'contain' }}
      />
    );
  }

  // 8. Business / MSME (CGTMSE, ASPIRE, NSIC, ZED)
  if (scheme.categories?.includes('business')) {
    return (
      <img
        src={msmeOriginal}
        alt="MSME"
        className="scheme-card-logo-img"
        style={{ width: '52px', height: '36px', objectFit: 'contain' }}
      />
    );
  }

  // 9. Social Welfare / Food / Pension / Housing
  if (scheme.categories?.includes('social-welfare')) {
    return (
      <svg width="46" height="46" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="24" cy="24" r="22" fill="#F0FDF4" stroke="#BBF7D0" strokeWidth="1" />
        {/* Protective Hands & Care Heart */}
        <path d="M14 26C14 22 18 18 24 18C30 18 34 22 34 26V32H14V26Z" fill="#087443" />
        <circle cx="24" cy="14" r="4" fill="#087443" />
        <path d="M10 36H38" stroke="#E98A00" strokeWidth="3" strokeLinecap="round" />
      </svg>
    );
  }

  // Default: Official Lion Capital of Ashoka
  return (
    <img
      src={ashokStambhOriginal}
      alt="State Emblem of India"
      className="scheme-card-logo-img"
      style={{ width: '42px', height: '52px', objectFit: 'contain' }}
    />
  );
}
