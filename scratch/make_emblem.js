const fs = require('fs');
let svg = fs.readFileSync('FrontEnd/src/assets/emblem_of_india.svg', 'utf8');

// Inject beautiful warm bronze-gold gradient
const defs = '<defs><linearGradient id="ashokGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#C59B4B"/><stop offset="45%" stop-color="#9A6B1F"/><stop offset="100%" stop-color="#604011"/></linearGradient></defs>';
svg = svg.replace('<svg ', '<svg fill="url(#ashokGold)" ');
svg = svg.replace('<title>Emblem of India</title>', defs + '<title>Emblem of India</title>');

fs.writeFileSync('FrontEnd/src/assets/ashok_stambh_vector.svg', svg);
console.log('Saved FrontEnd/src/assets/ashok_stambh_vector.svg successfully!');
