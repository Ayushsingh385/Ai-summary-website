import { useState } from 'react';
import { FiDownload, FiFileText, FiChevronDown } from 'react-icons/fi';

const TEMPLATES = [
  { value: '', label: '📄 Plain (Default)' },
  { value: 'zp_official', label: '🏛️ Zilla Parishad Official' },
  { value: 'court_order', label: '⚖️ Court Order Format' },
  { value: 'general', label: '📋 General Administrative' },
];

const DownloadBar = ({ onDownload, isDownloading, disabled, activeTab }) => {
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);

  const currentLabel = TEMPLATES.find(t => t.value === selectedTemplate)?.label || 'Plain (Default)';

  return (
    <div className="glass-panel fade-in" style={{
      marginTop: '2rem',
      padding: '1.5rem',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: '1rem'
    }}>
      <h3 style={{ color: 'var(--text-main)' }}>Export Results</h3>

      {/* Template Selector */}
      <div style={{ position: 'relative', width: '260px' }}>
        <button
          onClick={() => setShowTemplateMenu(!showTemplateMenu)}
          style={{
            width: '100%',
            padding: '0.55rem 1rem',
            background: 'var(--bg-card)',
            border: '1px solid var(--panel-border)',
            borderRadius: '8px',
            color: 'var(--text-main)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.9rem',
            transition: 'border-color 0.2s',
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--panel-border)'}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <FiFileText size={14} style={{ color: 'var(--accent-primary)' }} />
            {currentLabel}
          </span>
          <FiChevronDown size={14} style={{
            transform: showTemplateMenu ? 'rotate(180deg)' : 'rotate(0)',
            transition: 'transform 0.2s'
          }} />
        </button>

        {showTemplateMenu && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: '4px',
            background: 'var(--bg-card)',
            border: '1px solid var(--panel-border)',
            borderRadius: '8px',
            overflow: 'hidden',
            zIndex: 50,
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          }}>
            {TEMPLATES.map(t => (
              <button
                key={t.value}
                onClick={() => { setSelectedTemplate(t.value); setShowTemplateMenu(false); }}
                style={{
                  width: '100%',
                  padding: '0.6rem 1rem',
                  background: selectedTemplate === t.value ? 'rgba(124, 58, 237, 0.15)' : 'transparent',
                  border: 'none',
                  color: selectedTemplate === t.value ? 'var(--accent-primary)' : 'var(--text-main)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.88rem',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(124, 58, 237, 0.1)'}
                onMouseLeave={e => e.currentTarget.style.background = selectedTemplate === t.value ? 'rgba(124, 58, 237, 0.15)' : 'transparent'}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div style={{
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
        marginTop: '-0.5rem',
      }}>
        Template applies to DOCX exports only
      </div>

      {/* Download buttons */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
        {activeTab === 'summary' && (
          <>
            <button
              className="btn btn-outline"
              onClick={() => onDownload('txt', 'summary', null)}
              disabled={isDownloading || disabled}
            >
              <FiDownload /> TXT
            </button>

            <button
              className="btn btn-outline"
              onClick={() => onDownload('docx', 'summary', selectedTemplate || null)}
              disabled={isDownloading || disabled}
              style={{ borderColor: 'var(--accent-secondary)' }}
            >
              <FiDownload /> DOCX
            </button>
          </>
        )}

        {activeTab === 'original' && (
          <button
            className="btn btn-outline"
            onClick={() => onDownload('docx', 'original', selectedTemplate || null)}
            disabled={isDownloading || disabled}
            style={{ borderColor: 'var(--accent-secondary)' }}
          >
            <FiDownload /> Original DOCX
          </button>
        )}

        <button
          className="btn btn-primary"
          onClick={() => onDownload('pdf', activeTab, null)}
          disabled={isDownloading || disabled}
        >
          <FiDownload />
          {activeTab === 'summary' ? 'PDF Summary' : 'PDF Original'}
        </button>
      </div>
    </div>
  );
};

export default DownloadBar;
