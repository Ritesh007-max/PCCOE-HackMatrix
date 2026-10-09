/**
 * Dropdown Positioning Utility for Floating Portal Menus
 * FIN — Financial Policy Intelligence
 *
 * Computes exact viewport-safe fixed coordinates:
 * - Detects available space above vs below the trigger anchor
 * - Automatically flips menu upward when insufficient space below
 * - Clamps horizontal position inside viewport boundaries (min 12px margin)
 * - Restricts maxHeight to prevent vertical viewport overflow
 */

export function computeDropdownPosition(anchorRect, viewportWidth = 1280, viewportHeight = 800, options = {}) {
  if (!anchorRect) {
    return {
      style: { display: 'none' },
      openUpward: false,
    };
  }

  const menuWidth = options.menuWidth || 180;
  const menuHeight = options.menuHeight || 185; // typical height for 5 action items
  const gap = options.gap || 4;
  const edgeMargin = options.edgeMargin || 12;

  const spaceBelow = viewportHeight - anchorRect.bottom;
  const spaceAbove = anchorRect.top;

  // Flip upward if insufficient room below and more room above
  const openUpward = spaceBelow < menuHeight + gap && spaceAbove > spaceBelow;

  // Horizontal position: right-align to trigger button
  let right = viewportWidth - anchorRect.right;
  if (right < edgeMargin) {
    right = edgeMargin;
  }

  // Ensure menu doesn't overflow left edge of viewport
  const calculatedLeft = viewportWidth - right - menuWidth;
  if (calculatedLeft < edgeMargin) {
    right = Math.max(edgeMargin, viewportWidth - menuWidth - edgeMargin);
  }

  const maxHeight = openUpward
    ? Math.max(120, Math.min(340, spaceAbove - gap - edgeMargin))
    : Math.max(120, Math.min(340, spaceBelow - gap - edgeMargin));

  const style = {
    position: 'fixed',
    zIndex: 1050,
    width: `${menuWidth}px`,
    maxWidth: `calc(100vw - ${edgeMargin * 2}px)`,
    maxHeight: `${maxHeight}px`,
    overflowY: 'auto',
  };

  if (openUpward) {
    style.bottom = `${viewportHeight - anchorRect.top + gap}px`;
    style.right = `${right}px`;
  } else {
    style.top = `${anchorRect.bottom + gap}px`;
    style.right = `${right}px`;
  }

  // Clamp on very small mobile viewports (<= 360px)
  if (viewportWidth <= 360) {
    style.width = `calc(100vw - ${edgeMargin * 2}px)`;
    style.right = `${edgeMargin}px`;
  }

  return {
    style,
    openUpward,
    spaceBelow,
    spaceAbove,
    maxHeight,
  };
}
