import React from 'react';

// Tricolor wave next to FIN wordmark
export function TricolorWave({ className = '', style = {} }) {
  return (
    <svg
      width="32"
      height="26"
      viewBox="0 0 36 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={style}
      aria-hidden="true"
    >
      {/* Saffron stroke */}
      <path
        d="M2 7C10 2 24 1 34 5"
        stroke="#E98A00"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
      {/* White/Ivory subtle center stroke */}
      <path
        d="M2 14C10 9 24 8 34 12"
        stroke="#FFFFFF"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      {/* Green stroke */}
      <path
        d="M2 21C10 16 24 15 34 19"
        stroke="#087443"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

// Small subtle tricolor ribbon accent used beneath government quotes
export function TricolorRibbon({ width = 48, height = 5, className = '', style = {} }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 60 6"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{ display: 'inline-block', ...style }}
      aria-hidden="true"
    >
      <path d="M0 3C18 0 42 6 60 2" stroke="#E98A00" strokeWidth="2" strokeLinecap="round" />
      <path d="M6 4C24 1 48 7 60 4" stroke="#087443" strokeWidth="2" strokeLinecap="round" opacity="0.9" />
    </svg>
  );
}

// Lion Capital of Ashoka (State Emblem of India) authentic SVG icon
export function AshokaEmblem({ size = 32, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Government of India Emblem"
    >
      {/* Lions silhouette */}
      <path
        d="M12 2C10.5 2 9 3 9 4.5C9 5.5 9.5 6 10 6.5C8.5 7 7.5 8.5 7.5 10C7.5 11.5 8.5 12.8 10 13.2V15H14V13.2C15.5 12.8 16.5 11.5 16.5 10C16.5 8.5 15.5 7 14 6.5C14.5 6 15 5.5 15 4.5C15 3 13.5 2 12 2Z"
        fill="#5A4A32"
      />
      <circle cx="12" cy="5" r="1.5" fill="#3D3020" />
      <circle cx="8.5" cy="9.5" r="1" fill="#3D3020" />
      <circle cx="15.5" cy="9.5" r="1" fill="#3D3020" />
      {/* Abacus / Base */}
      <rect x="5" y="16" width="14" height="2" rx="0.5" fill="#5A4A32" />
      {/* Ashoka Chakra in center */}
      <circle cx="12" cy="20" r="2.5" stroke="#005B50" strokeWidth="1" />
      <circle cx="12" cy="20" r="0.8" fill="#005B50" />
      {/* Plinth */}
      <path d="M4 23H20L18 25H6L4 23Z" fill="#5A4A32" />
    </svg>
  );
}

// MSME Ministry Emblem / Logo
export function MsmeLogo({ size = 32 }) {
  return (
    <div
      style={{
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid #D0D5DD',
        borderRadius: '4px',
        padding: '3px 6px',
        backgroundColor: '#FFFFFF',
        fontFamily: 'var(--font-sans)',
        lineHeight: 1,
      }}
    >
      <span style={{ fontSize: '13px', fontWeight: '800', letterSpacing: '-0.03em', color: '#10243A' }}>
        MSME
      </span>
      <span style={{ fontSize: '6px', fontWeight: '600', color: '#667085', textTransform: 'uppercase', marginTop: '1px' }}>
        Govt of India
      </span>
    </div>
  );
}

// Kisan Green Sprout Logo
export function KisanSprout({ size = 28 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Agriculture Support"
    >
      <path
        d="M12 22V10M12 10C12 5.5 16 3 20 4C20 8 17.5 11 12 10ZM12 14C12 11 9 9 5 10C5 13 7.5 15 12 14Z"
        stroke="#087443"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
