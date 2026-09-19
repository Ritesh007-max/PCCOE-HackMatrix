const fs = require('fs');

// 1. Valid XML MSME vector SVG (No illegal HTML entities)
const msmeSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 80" width="200" height="80">
  <g fill="#10243A">
    <!-- M1 -->
    <path d="M10 8 C10 4 14 0 20 0 H28 C34 0 38 4 38 10 V52 H28 V16 H22 V52 H10 Z" />
    <path d="M32 10 C32 4 36 0 42 0 H50 C56 0 60 4 60 10 V52 H50 V16 H44 V52 H32 Z" />
    
    <!-- S -->
    <path d="M72 0 H106 V14 H88 V24 H104 C110 24 112 28 112 34 V44 C112 50 108 52 102 52 H68 V38 H92 V32 H76 C70 32 68 28 68 22 V10 C68 4 72 0 78 0 Z" />
    
    <!-- M2 -->
    <path d="M120 8 C120 4 124 0 130 0 H138 C144 0 148 4 148 10 V52 H138 V16 H132 V52 H120 Z" />
    <path d="M142 10 C142 4 146 0 152 0 H160 C166 0 170 4 170 10 V52 H160 V16 H154 V52 H142 Z" />
    
    <!-- E -->
    <path d="M178 0 H200 V14 H188 V20 H198 V32 H188 V38 H200 V52 H178 Z" />
    
    <!-- English Subtitle -->
    <text x="10" y="65" font-family="Inter, system-ui, sans-serif" font-size="7.5" font-weight="800" letter-spacing="0.5">MICRO, SMALL &amp; MEDIUM ENTERPRISES</text>
    <!-- Hindi Subtitle -->
    <text x="10" y="76" font-family="Inter, system-ui, sans-serif" font-size="6.5" font-weight="700" letter-spacing="0.3" fill="#475467">सूक्ष्म, लघु एवं मध्यम उद्यम मंत्रालय</text>
  </g>
</svg>`;

fs.writeFileSync('FrontEnd/src/assets/msme_logo_vector.svg', msmeSvg);
console.log('Fixed msme_logo_vector.svg');

// 2. Bold, vibrant PM Kisan agricultural sprout SVG matching reference
const kisanSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 90" width="80" height="90">
  <!-- Central Stem -->
  <path d="M40 88 V22" stroke="#06582A" stroke-width="4.5" stroke-linecap="round"/>
  
  <!-- Top Center Leaf (Vertical) -->
  <path d="M40 6 C32 16 34 30 40 38 C46 30 48 16 40 6 Z" fill="#0A7A3E"/>
  
  <!-- Middle Left Leaf -->
  <path d="M38 38 C22 30 10 38 8 50 C18 54 30 48 38 40 Z" fill="#086E37"/>
  
  <!-- Middle Right Leaf (Golden Grain / Corn) -->
  <path d="M42 38 C58 30 70 38 72 50 C62 54 50 48 42 40 Z" fill="#D99B16"/>
  <path d="M42 38 C50 34 60 40 64 48 C56 50 48 46 42 40 Z" fill="#F3BF38"/>
  
  <!-- Bottom Left Leaf -->
  <path d="M38 56 C20 50 8 60 6 72 C18 74 32 68 38 58 Z" fill="#054A23"/>
  
  <!-- Bottom Right Leaf -->
  <path d="M42 56 C60 50 72 60 74 72 C62 74 48 68 42 58 Z" fill="#054A23"/>
</svg>`;

fs.writeFileSync('FrontEnd/src/assets/kisan_logo_vector.svg', kisanSvg);
console.log('Fixed kisan_logo_vector.svg');
