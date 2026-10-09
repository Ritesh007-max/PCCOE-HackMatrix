import React from 'react';

/**
 * Validates whether a URL has a safe protocol for web links.
 * Whitelists only https://, http://, and mailto:.
 * Blocks javascript:, data:, vbscript:, and other unsafe protocols.
 */
export const isSafeUrl = (url) => {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim().toLowerCase();
  return trimmed.startsWith('https://') || trimmed.startsWith('http://') || trimmed.startsWith('mailto:') || (trimmed.startsWith('/') && !trimmed.startsWith('//'));
};

/**
 * Tokenizes and renders inline Markdown tokens:
 * - Links: [label](URL) with protocol safety check and external target="_blank"
 * - Bold: **text**
 * - Inline code: `code`
 * - Italic: *text*
 * - Parens wrapping links: ([label](URL)) correctly preserved
 */
export const renderMarkdownInline = (text, onNavigate = null) => {
  if (!text) return null;
  const tokens = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    const codeMatch = remaining.match(/`([^`]+)`/);
    const italicMatch = remaining.match(/(?<!\*)\*([^*]+)\*(?!\*)/);
    // Link regex: [label](url) where url allows balanced parentheses
    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^()\s]+(?:\([^()\s]+\)[^()\s]*)*)\)/);

    let earliest = null;
    let type = null;

    if (boldMatch && (earliest === null || boldMatch.index < earliest.index)) {
      earliest = boldMatch;
      type = 'bold';
    }
    if (codeMatch && (earliest === null || codeMatch.index < earliest.index)) {
      earliest = codeMatch;
      type = 'code';
    }
    if (italicMatch && (earliest === null || italicMatch.index < earliest.index)) {
      earliest = italicMatch;
      type = 'italic';
    }
    if (linkMatch && (earliest === null || linkMatch.index < earliest.index)) {
      earliest = linkMatch;
      type = 'link';
    }

    if (!earliest) {
      tokens.push(React.createElement('span', { key: keyIdx++ }, remaining));
      break;
    }

    if (earliest.index > 0) {
      tokens.push(React.createElement('span', { key: keyIdx++ }, remaining.slice(0, earliest.index)));
    }

    if (type === 'bold') {
      tokens.push(
        React.createElement('strong', {
          key: keyIdx++,
          style: { fontWeight: 650, color: 'inherit' }
        }, earliest[1])
      );
    } else if (type === 'code') {
      tokens.push(
        React.createElement('code', {
          key: keyIdx++,
          style: {
            backgroundColor: '#F2F4F7',
            color: '#1D2939',
            padding: '1px 5px',
            borderRadius: '4px',
            fontSize: '0.9em',
            fontFamily: 'monospace'
          }
        }, earliest[1])
      );
    } else if (type === 'italic') {
      tokens.push(React.createElement('em', { key: keyIdx++ }, earliest[1]));
    } else if (type === 'link') {
      const label = earliest[1];
      const url = earliest[2].trim();
      if (isSafeUrl(url)) {
        const isInternal = url.startsWith('/');
        tokens.push(
          React.createElement('a', {
            key: keyIdx++,
            href: url,
            target: isInternal ? undefined : '_blank',
            rel: isInternal ? undefined : 'noopener noreferrer',
            onClick: isInternal && onNavigate ? (e) => {
              e.preventDefault();
              onNavigate(url);
            } : undefined,
            style: {
              color: '#2563EB',
              textDecoration: 'underline',
              textUnderlineOffset: '2px',
              fontWeight: 500,
              cursor: 'pointer',
              wordBreak: 'break-word'
            }
          }, label)
        );
      } else {
        // Invalid protocol must remain inert plain text (no <a> tag, safe plain string)
        tokens.push(React.createElement('span', { key: keyIdx++ }, earliest[0]));
      }
    }

    remaining = remaining.slice(earliest.index + earliest[0].length);
  }

  return tokens;
};

/**
 * Lightweight Markdown block renderer:
 * - H1 (# ), H2 (## ), H3 (### ), H4 (#### )
 * - Blockquotes (> )
 * - Ordered lists (1. ) and Unordered lists (- or • or *)
 * - Horizontal rules (---, ***, ___)
 * - Paragraphs
 */
export const MarkdownRenderer = ({ content, onNavigate = null }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let currentList = null;
  let currentBlockquote = null;
  let keyCounter = 0;

  const flushList = () => {
    if (currentList) {
      if (currentList.type === 'ul') {
        elements.push(
          React.createElement('ul', {
            key: keyCounter++,
            style: { margin: '4px 0 8px 18px', padding: 0, listStyleType: 'disc' }
          }, currentList.items.map((it, i) =>
            React.createElement('li', { key: i, style: { marginBottom: '3px' } },
              renderMarkdownInline(it, onNavigate)
            )
          ))
        );
      } else {
        elements.push(
          React.createElement('ol', {
            key: keyCounter++,
            style: { margin: '4px 0 8px 18px', padding: 0 }
          }, currentList.items.map((it, i) =>
            React.createElement('li', { key: i, style: { marginBottom: '3px' } },
              renderMarkdownInline(it, onNavigate)
            )
          ))
        );
      }
      currentList = null;
    }
  };

  const flushBlockquote = () => {
    if (currentBlockquote) {
      elements.push(
        React.createElement('blockquote', {
          key: keyCounter++,
          style: {
            margin: '6px 0 8px 0',
            padding: '8px 12px',
            borderLeft: '3px solid #2563EB',
            backgroundColor: '#F8FAFC',
            color: '#344054',
            fontSize: '13px',
            borderRadius: '0 4px 4px 0',
            lineHeight: 1.45
          }
        }, currentBlockquote.map((line, idx) =>
          React.createElement('div', {
            key: idx,
            style: { marginBottom: idx < currentBlockquote.length - 1 ? '4px' : 0 }
          }, renderMarkdownInline(line, onNavigate))
        ))
      );
      currentBlockquote = null;
    }
  };

  const flushAll = () => {
    flushList();
    flushBlockquote();
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      flushAll();
      continue;
    }

    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      flushAll();
      elements.push(
        React.createElement('hr', {
          key: keyCounter++,
          style: { border: 'none', borderTop: '1px solid #EAECF0', margin: '10px 0' }
        })
      );
      continue;
    }

    // Blockquote: > text
    if (trimmed.startsWith('>')) {
      flushList();
      const quoteText = trimmed.replace(/^>\s?/, '');
      if (!currentBlockquote) currentBlockquote = [];
      currentBlockquote.push(quoteText);
      continue;
    }

    // Headings (checked from most specific #### down to #)
    if (trimmed.startsWith('#### ')) {
      flushAll();
      elements.push(
        React.createElement('h5', {
          key: keyCounter++,
          style: { margin: '8px 0 4px 0', fontSize: '13px', fontWeight: 700, color: '#101828' }
        }, renderMarkdownInline(trimmed.slice(5), onNavigate))
      );
      continue;
    }

    if (trimmed.startsWith('### ')) {
      flushAll();
      elements.push(
        React.createElement('h4', {
          key: keyCounter++,
          style: { margin: '10px 0 4px 0', fontSize: '14px', fontWeight: 700, color: '#101828' }
        }, renderMarkdownInline(trimmed.slice(4), onNavigate))
      );
      continue;
    }

    if (trimmed.startsWith('## ')) {
      flushAll();
      elements.push(
        React.createElement('h3', {
          key: keyCounter++,
          style: { margin: '12px 0 5px 0', fontSize: '15px', fontWeight: 700, color: '#101828' }
        }, renderMarkdownInline(trimmed.slice(3), onNavigate))
      );
      continue;
    }

    if (trimmed.startsWith('# ')) {
      flushAll();
      elements.push(
        React.createElement('h2', {
          key: keyCounter++,
          style: { margin: '14px 0 6px 0', fontSize: '16px', fontWeight: 700, color: '#101828' }
        }, renderMarkdownInline(trimmed.slice(2), onNavigate))
      );
      continue;
    }

    // Unordered lists: - or • or *
    const bulletMatch = trimmed.match(/^[-•*]\s+(.*)$/);
    if (bulletMatch) {
      flushBlockquote();
      if (!currentList || currentList.type !== 'ul') {
        flushList();
        currentList = { type: 'ul', items: [] };
      }
      currentList.items.push(bulletMatch[1]);
      continue;
    }

    // Numbered lists: 1. or 2.
    const numMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (numMatch) {
      flushBlockquote();
      if (!currentList || currentList.type !== 'ol') {
        flushList();
        currentList = { type: 'ol', items: [] };
      }
      currentList.items.push(numMatch[1]);
      continue;
    }

    // Normal paragraph
    flushAll();
    elements.push(
      React.createElement('p', {
        key: keyCounter++,
        style: { margin: '0 0 6px 0', lineHeight: 1.45 }
      }, renderMarkdownInline(trimmed, onNavigate))
    );
  }

  flushAll();
  return React.createElement('div', { className: 'fin-markdown-content' }, elements);
};

export default MarkdownRenderer;
