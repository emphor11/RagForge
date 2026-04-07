import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

const DocumentViewer = ({ rawText, highlightQuote, onClose }) => {
  const contentRef = useRef(null);

  useEffect(() => {
    if (highlightQuote && contentRef.current) {
      const marks = contentRef.current.querySelectorAll('mark');
      if (marks.length > 0) {
        marks[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [highlightQuote, rawText]);

  if (!rawText || !highlightQuote) return null;

  let displayHtml = rawText.replace(/\n/g, '<br/>');

  if (highlightQuote && highlightQuote.trim() !== '') {
    const escapedQuote = highlightQuote
      .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/\s+/g, '\\s+');

    try {
      const regex = new RegExp(`(${escapedQuote})`, 'gi');
      displayHtml = displayHtml.replace(
        regex,
        '<mark style="background-color: var(--warning-bg); color: var(--text-primary); font-weight: 600; padding: 1px 4px; border-radius: 3px; border-bottom: 2px solid var(--warning);">$1</mark>'
      );
    } catch (e) {
      console.error("Regex rendering error:", e);
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0, right: 0, bottom: 0, left: 0,
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 9999,
      padding: '40px'
    }}>
      <div style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-default)',
        borderRadius: '8px',
        width: '100%',
        maxWidth: '900px',
        height: '100%',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.25)'
      }}>
        {/* Header */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-default)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h3 style={{
            margin: 0,
            color: 'var(--text-primary)',
            fontSize: '14px',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            Source Verification
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div
          ref={contentRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 32px',
            color: 'var(--text-body)',
            fontSize: '14px',
            lineHeight: '1.8',
            fontFamily: 'var(--font)'
          }}
          dangerouslySetInnerHTML={{ __html: displayHtml }}
        />
      </div>
    </div>
  );
};

export default DocumentViewer;
