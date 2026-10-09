import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { Search, X, Check, ChevronDown, ChevronUp, AlertCircle, Loader2 } from 'lucide-react';
import { isCentralScheme } from '../../utils/documentSchemeValidation';

/**
 * SchemeReadinessCombobox
 * Accessible, lightweight searchable combobox/popover for selecting government schemes.
 * Replaces the oversized browser-native select overlay.
 *
 * Conforms to W3C ARIA Combobox design pattern:
 * - Search schemes by name, keyword, or identifier
 * - Viewport-relative bounded height with internal vertical scrolling
 * - Outside click and Escape key dismissal
 * - Full keyboard navigation (Arrow Up/Down, Enter, Tab)
 * - Result count feedback and empty/loading states
 */
export default function SchemeReadinessCombobox({
  schemes = [],
  selectedSchemeId = '',
  onSelectScheme,
  isLoading = false,
  error = null,
  policyState = 'Gujarat',
  disabled = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const containerRef = useRef(null);
  const triggerRef = useRef(null);
  const inputRef = useRef(null);
  const listboxRef = useRef(null);

  // Find currently selected scheme
  const selectedScheme = useMemo(() => {
    if (!selectedSchemeId || !schemes || schemes.length === 0) return null;
    return schemes.find((s) => s.id === selectedSchemeId) || null;
  }, [schemes, selectedSchemeId]);

  // Filter schemes based on search query
  const filteredSchemes = useMemo(() => {
    if (!searchQuery.trim()) return schemes;
    const q = searchQuery.toLowerCase().trim();
    return schemes.filter((s) => {
      const name = (s.name || s.scheme_name || '').toLowerCase();
      const id = (s.id || '').toLowerCase();
      const benefit = (s.benefit || s.benefit_summary || '').toLowerCase();
      const ministry = (s.ministry || s.department || '').toLowerCase();
      return name.includes(q) || id.includes(q) || benefit.includes(q) || ministry.includes(q);
    });
  }, [schemes, searchQuery]);

  // Reset highlighted index when filter results change
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [searchQuery, isOpen]);

  // Auto-focus search input when opened
  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
        }
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Dismiss on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('touchstart', handleOutsideClick);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('touchstart', handleOutsideClick);
    };
  }, [isOpen]);

  // Dismiss on Escape key & keyboard handler on container
  const handleKeyDown = useCallback(
    (e) => {
      if (!isOpen) {
        if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setIsOpen(true);
        }
        return;
      }

      if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
        return;
      }

      if (e.key === 'Tab') {
        setIsOpen(false);
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlightedIndex((prev) => {
          const next = prev < filteredSchemes.length - 1 ? prev + 1 : 0;
          scrollItemIntoView(next);
          return next;
        });
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlightedIndex((prev) => {
          const next = prev > 0 ? prev - 1 : filteredSchemes.length - 1;
          scrollItemIntoView(next);
          return next;
        });
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < filteredSchemes.length) {
          const chosen = filteredSchemes[highlightedIndex];
          handleSelect(chosen.id);
        } else if (filteredSchemes.length === 1) {
          handleSelect(filteredSchemes[0].id);
        }
      }
    },
    [isOpen, filteredSchemes, highlightedIndex]
  );

  const scrollItemIntoView = (index) => {
    if (!listboxRef.current) return;
    const items = listboxRef.current.querySelectorAll('.checker-combobox-option');
    if (items[index]) {
      items[index].scrollIntoView({ block: 'nearest' });
    }
  };

  const handleSelect = (schemeId) => {
    if (typeof onSelectScheme === 'function') {
      onSelectScheme(schemeId);
    }
    setIsOpen(false);
    setSearchQuery('');
    triggerRef.current?.focus();
  };

  const toggleDropdown = () => {
    if (disabled || isLoading) return;
    setIsOpen((prev) => !prev);
  };

  const triggerLabel = selectedScheme
    ? selectedScheme.name
    : `-- Select from ${schemes.length} Schemes (${policyState || 'Gujarat'} & Central) --`;

  return (
    <div
      className="checker-combobox-wrapper"
      ref={containerRef}
      onKeyDown={handleKeyDown}
    >
      {/* Combobox Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        className={`checker-combobox-trigger ${isOpen ? 'active' : ''} ${selectedScheme ? 'has-selection' : ''}`}
        onClick={toggleDropdown}
        disabled={disabled || isLoading}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls="checker-schemes-listbox"
        aria-label="Select scheme to check document readiness"
        title={selectedScheme ? selectedScheme.name : triggerLabel}
      >
        <span className="checker-combobox-trigger-text">
          {triggerLabel}
        </span>
        <span className="checker-combobox-trigger-icon" aria-hidden="true">
          {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div
          className="checker-combobox-popover"
          role="region"
          aria-label="Scheme selector popover"
        >
          {/* Integrated Search Bar inside Popover */}
          <div className="checker-search-bar checker-combobox-search-bar">
            <Search size={13} color="#667085" className="checker-search-icon" aria-hidden="true" />
            <input
              ref={inputRef}
              type="search"
              className="checker-search-input checker-combobox-search-input"
              placeholder={`Search ${schemes.length} schemes...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search applicable schemes"
              autoComplete="off"
              spellCheck="false"
            />
            {searchQuery && (
              <button
                type="button"
                className="checker-search-clear-btn"
                onClick={() => {
                  setSearchQuery('');
                  inputRef.current?.focus();
                }}
                aria-label="Clear scheme search filter"
                title="Clear filter"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Results Count & Scope Header */}
          <div className="checker-combobox-count-bar">
            <span className="checker-combobox-count-text">
              {searchQuery.trim()
                ? `Showing ${filteredSchemes.length} of ${schemes.length} schemes`
                : `${schemes.length} schemes available (${policyState || 'Gujarat'} & Central)`}
            </span>
            {selectedScheme && (
              <button
                type="button"
                className="checker-combobox-clear-selection-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelect('');
                }}
                title="Clear selected scheme"
              >
                Clear choice
              </button>
            )}
          </div>

          {/* Scrollable Results Listbox */}
          <ul
            ref={listboxRef}
            id="checker-schemes-listbox"
            role="listbox"
            aria-label="Applicable government schemes"
            className="checker-combobox-list"
            tabIndex={-1}
          >
            {isLoading ? (
              <li className="checker-combobox-state-item" role="status">
                <Loader2 size={16} className="checker-spin" />
                <span>Loading official catalog schemes...</span>
              </li>
            ) : error ? (
              <li className="checker-combobox-state-item error" role="alert">
                <AlertCircle size={15} color="#D92D20" />
                <span>{error || 'Failed to load schemes'}</span>
              </li>
            ) : filteredSchemes.length === 0 ? (
              <li className="checker-combobox-state-item empty" role="option" aria-selected="false">
                <span>No schemes matching "{searchQuery}"</span>
                <button
                  type="button"
                  className="checker-combobox-reset-filter-btn"
                  onClick={() => setSearchQuery('')}
                >
                  Clear search
                </button>
              </li>
            ) : (
              filteredSchemes.map((scheme, idx) => {
                const isSelected = scheme.id === selectedSchemeId;
                const isHighlighted = idx === highlightedIndex;
                const isCentral = isCentralScheme(scheme);
                const badgeLabel = scheme.state || (isCentral ? 'Central' : policyState || 'Gujarat');

                return (
                  <li
                    key={scheme.id}
                    id={`scheme-opt-${scheme.id}`}
                    role="option"
                    aria-selected={isSelected}
                    className={`checker-combobox-option ${isSelected ? 'selected' : ''} ${isHighlighted ? 'highlighted' : ''}`}
                    onClick={() => handleSelect(scheme.id)}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    title={scheme.name}
                  >
                    <div className="checker-combobox-option-body">
                      <div className="checker-combobox-option-header">
                        <span className={`checker-combobox-badge ${isCentral ? 'central' : 'state'}`}>
                          {badgeLabel}
                        </span>
                        {isSelected && (
                          <span className="checker-combobox-check-icon" aria-hidden="true">
                            <Check size={13} strokeWidth={2.5} />
                          </span>
                        )}
                      </div>
                      <div className="checker-combobox-option-name">
                        {scheme.name}
                      </div>
                      {scheme.benefit && (
                        <div className="checker-combobox-option-benefit">
                          {scheme.benefit}
                        </div>
                      )}
                    </div>
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
