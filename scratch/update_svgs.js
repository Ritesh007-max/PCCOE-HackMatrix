const fs = require('fs');

// 1. Ashok Stambh Vector with Bronze-Gold Metallic Gradient
let ashokSvg = fs.readFileSync('FrontEnd/src/assets/emblem_of_india.svg', 'utf8');
const goldDefs = '<defs><linearGradient id="ashokGoldGrad" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#C8973E"/><stop offset="35%" stop-color="#9E7024"/><stop offset="75%" stop-color="#724D14"/><stop offset="100%" stop-color="#4F330A"/></linearGradient></defs>';

ashokSvg = ashokSvg.replace('<svg ', '<svg fill="url(#ashokGoldGrad)" ');
ashokSvg = ashokSvg.replace('<title>Emblem of India</title>', goldDefs + '<title>Emblem of India</title>');
ashokSvg = ashokSvg.replace(/style="-inkscape-stroke:none"/g, 'fill="url(#ashokGoldGrad)"');

fs.writeFileSync('FrontEnd/src/assets/ashok_stambh_vector.svg', ashokSvg);
console.log('1. ashok_stambh_vector.svg created successfully');

// 2. High-res vector for PM Kisan (Agricultural 5-leaf sprout with golden grain)
const kisanSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 110" width="100" height="110" fill="none">
  <!-- Central Stem -->
  <path d="M50 105 V25" stroke="#08542B" stroke-width="4.5" stroke-linecap="round"/>
  
  <!-- Top Center Leaf -->
  <path d="M50 15 C44 24 45 38 50 46 C55 38 56 24 50 15 Z" fill="#0A7A3E"/>
  
  <!-- Middle Left Leaf (Green) -->
  <path d="M48 48 C32 40 18 48 16 58 C26 62 40 58 48 50" fill="#0E8A46"/>
  <path d="M48 48 C32 40 18 48 16 58 C26 62 40 58 48 50 Z" stroke="#08542B" stroke-width="0.5"/>
  
  <!-- Middle Right Leaf (Golden Corn / Grain Seed) -->
  <path d="M52 48 C68 40 82 48 84 58 C74 62 60 58 52 50" fill="#E5A61E"/>
  <path d="M52 48 C68 40 82 48 84 58 C74 62 60 58 52 50 Z" stroke="#B87D0C" stroke-width="0.5"/>
  
  <!-- Bottom Left Leaf (Deep Green) -->
  <path d="M48 68 C28 62 14 74 12 86 C24 88 40 82 48 70" fill="#06582A"/>
  
  <!-- Bottom Right Leaf (Deep Green) -->
  <path d="M52 68 C72 62 86 74 88 86 C76 88 60 82 52 70" fill="#06582A"/>
</svg>`;

fs.writeFileSync('FrontEnd/src/assets/kisan_logo_vector.svg', kisanSvg);
console.log('2. kisan_logo_vector.svg created successfully');

// 3. High-res vector for MSME Logo
const msmeSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 100" width="240" height="100" fill="#10243A">
  <!-- M 1 -->
  <path d="M12 10 C12 6 16 2 22 2 H32 C38 2 42 6 42 12 V70 H30 V22 H24 V70 H12 Z" />
  <path d="M42 22 H48 V70 H36 V22 Z" opacity="0"/>
  <path d="M36 12 C36 6 40 2 46 2 H56 C62 2 66 6 66 12 V70 H54 V22 H48 V70 H36 Z" />
  
  <!-- S -->
  <path d="M78 2 H114 V18 H94 V32 H112 C118 32 120 36 120 42 V60 C120 66 116 70 110 70 H74 V54 H98 V44 H80 C74 44 72 40 72 34 V12 C72 6 76 2 82 2 Z" />
  
  <!-- M 2 -->
  <path d="M130 10 C130 6 134 2 140 2 H150 C156 2 160 6 160 12 V70 H148 V22 H142 V70 H130 Z" />
  <path d="M154 12 C154 6 158 2 164 2 H174 C180 2 184 6 184 12 V70 H172 V22 H166 V70 H154 Z" />
  
  <!-- E -->
  <path d="M194 2 H236 V18 H210 V28 H230 V42 H210 V54 H236 V70 H194 Z" />
  
  <!-- Subtitle Text: MICRO, SMALL & MEDIUM ENTERPRISES -->
  <text x="12" y="86" font-family="Inter, -apple-system, sans-serif" font-size="9" font-weight="700" letter-spacing="1.2" fill="#10243A">MICRO, SMALL &amp; MEDIUM ENTERPRISES</text>
  <text x="12" y="98" font-family="Inter, -apple-system, sans-serif" font-size="7.5" font-weight="600" letter-spacing="0.8" fill="#5A6B7C">MINISTRY OF MSME &bull; GOVT OF INDIA</text>
</svg>`;

fs.writeFileSync('FrontEnd/src/assets/msme_logo_vector.svg', msmeSvg);
console.log('3. msme_logo_vector.svg created successfully');
