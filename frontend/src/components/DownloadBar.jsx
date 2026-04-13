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
      paddingBottom: '3rem', // Extra room for the template dropdown
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
          className="select-trigger"
          style={{ width: '100%' }}
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
          <div className="dropdown-menu">
            {TEMPLATES.map(t => (
              <button
                key={t.value}
                onClick={() => { setSelectedTemplate(t.value); setShowTemplateMenu(false); }}
                className={`dropdown-item ${selectedTemplate === t.value ? 'selected' : ''}`}
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
