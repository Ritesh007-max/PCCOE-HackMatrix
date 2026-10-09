import test from 'node:test';
import assert from 'node:assert/strict';
import { isSafeUrl, renderMarkdownInline, MarkdownRenderer } from '../src/components/chat/markdownParser.js';

test('1. H4 heading rendering produces styled h5 element', () => {
  const markdown = '#### Stage 1: Call for Applications';
  const result = MarkdownRenderer({ content: markdown });

  assert.equal(result.type, 'div');
  const h4Element = result.props.children[0];
  assert.equal(h4Element.type, 'h5');
  assert.equal(h4Element.props.style.fontSize, '13px');
  assert.equal(h4Element.props.style.fontWeight, 700);

  // Content should match Stage 1
  const textChildren = h4Element.props.children;
  const combinedText = textChildren.map(c => c.props.children).join('');
  assert.equal(combinedText, 'Stage 1: Call for Applications');
});

test('2. Blockquote rendering wraps lines in styled blockquote', () => {
  const markdown = '> **Jurisdiction & Applicability:** This scheme operates under Kerala jurisdiction.\n> Additional note line.';
  const result = MarkdownRenderer({ content: markdown });

  const bq = result.props.children[0];
  assert.equal(bq.type, 'blockquote');
  assert.equal(bq.props.style.borderLeft, '3px solid #2563EB');
  assert.equal(bq.props.children.length, 2);

  // First line should have bold token
  const line1 = bq.props.children[0].props.children;
  const boldToken = line1.find(t => t.type === 'strong');
  assert.ok(boldToken, 'Blockquote line 1 should have bold token');
  assert.equal(boldToken.props.children, 'Jurisdiction & Applicability:');
});

test('3. Safe clickable HTTPS link rendered as anchor with target="_blank"', () => {
  const inline = renderMarkdownInline('Please download the [Prescribed Format](https://dbtindia.gov.in/guidelines) here.');
  const linkEl = inline.find(t => t.type === 'a');

  assert.ok(linkEl, 'Must render an <a> tag for safe https link');
  assert.equal(linkEl.props.href, 'https://dbtindia.gov.in/guidelines');
  assert.equal(linkEl.props.target, '_blank');
  assert.equal(linkEl.props.rel, 'noopener noreferrer');
  assert.equal(linkEl.props.children, 'Prescribed Format');
});

test('4. Mailto link rendered safely as anchor', () => {
  const inline = renderMarkdownInline('Contact us at [Support Email](mailto:helpdesk@dbtindia.gov.in) for queries.');
  const linkEl = inline.find(t => t.type === 'a');

  assert.ok(linkEl, 'Must render an <a> tag for mailto link');
  assert.equal(linkEl.props.href, 'mailto:helpdesk@dbtindia.gov.in');
  assert.equal(linkEl.props.target, '_blank');
  assert.equal(linkEl.props.rel, 'noopener noreferrer');
  assert.equal(linkEl.props.children, 'Support Email');
});

test('5. Rejection of javascript: and data: links renders inert text without anchor', () => {
  // Test javascript: link
  const inlineJs = renderMarkdownInline('Click [Exploit](javascript:alert(1)) now');
  const anchorJs = inlineJs.find(t => t.type === 'a');
  assert.equal(anchorJs, undefined, 'Must not render <a> tag for javascript: protocol');
  const inertJs = inlineJs.find(t => t.props.children === '[Exploit](javascript:alert(1))');
  assert.ok(inertJs, 'Must render raw inert text in a span');

  // Test data: link
  const inlineData = renderMarkdownInline('Open [Phishing](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==) file');
  const anchorData = inlineData.find(t => t.type === 'a');
  assert.equal(anchorData, undefined, 'Must not render <a> tag for data: protocol');
  const inertData = inlineData.find(t => t.props.children === '[Phishing](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)');
  assert.ok(inertData, 'Must render raw inert data link in a span');
});

test('6. External link security attributes enforced strictly', () => {
  assert.equal(isSafeUrl('https://secure.gov.in'), true);
  assert.equal(isSafeUrl('http://insecure.gov.in'), true);
  assert.equal(isSafeUrl('mailto:officer@gov.in'), true);
  assert.equal(isSafeUrl('javascript:void(0)'), false);
  assert.equal(isSafeUrl('vbscript:msgbox(1)'), false);
  assert.equal(isSafeUrl('data:text/plain;base64,SGVsbG8='), false);
  assert.equal(isSafeUrl('file:///etc/passwd'), false);
  assert.equal(isSafeUrl(''), false);
  assert.equal(isSafeUrl(null), false);
});

test('7. Nested parentheses around Markdown links handled cleanly', () => {
  const inline = renderMarkdownInline('Endorsement Form ([Prescribed Format](https://dbtindia.gov.in/guidelines)) required.');

  // Check that the anchor exists and has correct href
  const linkEl = inline.find(t => t.type === 'a');
  assert.ok(linkEl, 'Should parse link inside outer parentheses');
  assert.equal(linkEl.props.href, 'https://dbtindia.gov.in/guidelines');
  assert.equal(linkEl.props.children, 'Prescribed Format');

  // Verify that outer parentheses are present as separate text spans
  const spans = inline.filter(t => t.type === 'span').map(t => t.props.children);
  assert.ok(spans.some(s => s.includes('(')), 'Opening parenthesis should precede link');
  assert.ok(spans.some(s => s.includes(')')), 'Closing parenthesis should succeed link');
  assert.ok(!spans.some(s => s.includes('[Prescribed Format]')), 'Delimiters [ ] should not leak into text spans');
});

test('8. Existing bold, italic, code, and list rendering preserved', () => {
  // Inline tokens
  const inline = renderMarkdownInline('**Bold text** with `code token` and *italic text*');
  assert.equal(inline.find(t => t.type === 'strong')?.props.children, 'Bold text');
  assert.equal(inline.find(t => t.type === 'code')?.props.children, 'code token');
  assert.equal(inline.find(t => t.type === 'em')?.props.children, 'italic text');

  // Lists and headings in block renderer
  const doc = [
    '# Heading 1',
    '## Heading 2',
    '### Heading 3',
    '- Item 1',
    '- Item 2',
    '1. Step A',
    '2. Step B'
  ].join('\n');

  const rendered = MarkdownRenderer({ content: doc });
  const children = rendered.props.children;

  assert.equal(children[0].type, 'h2');
  assert.equal(children[1].type, 'h3');
  assert.equal(children[2].type, 'h4');
  assert.equal(children[3].type, 'ul');
  assert.equal(children[3].props.children.length, 2);
  assert.equal(children[4].type, 'ol');
  assert.equal(children[4].props.children.length, 2);
});
