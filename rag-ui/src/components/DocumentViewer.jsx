import React, { useEffect, useRef } from 'react';

const DocumentViewer = ({ rawText, highlightQuote, onClose }) => {
  const contentRef = useRef(null);

  useEffect(() => {
    if (highlightQuote && contentRef.current) {
      // Find the mark element and scroll it into view
      const marks = contentRef.current.querySelectorAll('mark');
      if (marks.length > 0) {
        marks[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [highlightQuote, rawText]);

  if (!rawText || !highlightQuote) return null;

  // Build the highlighted HTML
  let displayHtml = rawText.replace(/\n/g, '<br/>');

  if (highlightQuote && highlightQuote.trim() !== '') {
    // Escape regex characters from the quote and make whitespace flexible
    const escapedQuote = highlightQuote
      .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/\s+/g, '\\s+');
      
    try {
      const regex = new RegExp(`(${escapedQuote})`, 'gi');
      displayHtml = displayHtml.replace(regex, '<mark class="source-highlight" style="background-color: #fde047; color: #000; font-weight: bold; padding: 0 4px; border-radius: 4px;">$1</mark>');
    } catch (e) {
      console.error("Regex rendering error:", e);
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0, right: 0, bottom: 0, left: 0,
      backgroundColor: 'rgba(0,0,0,0.8)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,
      padding: '40px'
    }}>
      <div style={{
        backgroundColor: '#111827',
        border: '1px solid #374151',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '900px',
        height: '100%',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid #374151',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#1f2937',
          borderTopLeftRadius: '12px',
          borderTopRightRadius: '12px'
        }}>
          <h3 style={{ margin: 0, color: '#f3f4f6', fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            📄 Source Verification Viewer
          </h3>
          <button 
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#9ca3af',
              cursor: 'pointer',
              fontSize: '18px',
              padding: '4px'
            }}
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div 
          ref={contentRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '32px',
            color: '#d1d5db',
            fontSize: '14px',
            lineHeight: '1.8',
            fontFamily: 'Inter, sans-serif'
          }}
          dangerouslySetInnerHTML={{ __html: displayHtml }}
        />
      </div>
    </div>
  );
};

export default DocumentViewer;
