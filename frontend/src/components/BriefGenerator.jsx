import { useState } from 'react';
import { FiFileText, FiDownload, FiCheck } from 'react-icons/fi';
import axios from 'axios';

const BRIEF_TYPES = [
  { value: 'memo', label: 'Legal Memorandum' },
  { value: 'brief', label: 'Legal Brief' },
  { value: 'opinion', label: 'Legal Opinion' },
  { value: 'summary', label: 'Case Summary' },
];

const TEMPLATES = [
  { value: 'general', label: 'General / Clean' },
  { value: 'zp_official', label: 'Zilla Parishad Official' },
  { value: 'court_order', label: 'Court Order Format' },
];

const BriefGenerator = ({ originalText, summaryResult, keywords, caseType, legalAnalysis, filename }) => {
  const [briefType, setBriefType] = useState('memo');
  const [template, setTemplate] = useState('general');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);

  const handleGenerate = async () => {
    if (!originalText || !summaryResult?.summary) return;

    setIsGenerating(true);
    setGenerated(false);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        'http://localhost:8000/api/brief',
        {
          filename: filename || 'Case Document',
          original_text: originalText,
          summary: summaryResult.summary,
          keywords: keywords || [],
          legal_analysis: legalAnalysis,
          case_type: caseType,
          brief_type: briefType,
          template,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          responseType: 'blob',
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `legal_${briefType}_${Date.now()}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      setGenerated(true);
    } catch (err) {
      console.error('Brief generation failed:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div style={{
      marginTop: '1.5rem',
      padding: '1.25rem',
      background: 'var(--bg-card)',
      border: '1px solid var(--panel-border)',
      borderRadius: '10px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <FiFileText size={18} style={{ color: 'var(--accent-primary)' }} />
        <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-main)' }}>
          Generate Legal Brief
        </h3>
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Create a structured legal document with Issues, Facts, Analysis, Prayer, and Authorities sections.
      </p>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div style={{ flex: '1 1 150px' }}>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>
            Brief Type
          </label>
          <select
            value={briefType}
            onChange={e => setBriefType(e.target.value)}
            style={{
              width: '100%',
              padding: '0.4rem 0.6rem',
              fontSize: '0.85rem',
              background: 'var(--bg-dark)',
              color: 'var(--text-main)',
              border: '1px solid var(--panel-border)',
              borderRadius: '6px',
              outline: 'none',
            }}
          >
            {BRIEF_TYPES.map(bt => (
              <option key={bt.value} value={bt.value} style={{ background: 'var(--bg-dark)', color: 'var(--text-main)' }}>{bt.label}</option>
            ))}
          </select>
        </div>

        <div style={{ flex: '1 1 150px' }}>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>
            Document Template
          </label>
          <select
            value={template}
            onChange={e => setTemplate(e.target.value)}
            style={{
              width: '100%',
              padding: '0.4rem 0.6rem',
              fontSize: '0.85rem',
              background: 'var(--bg-dark)',
              color: 'var(--text-main)',
              border: '1px solid var(--panel-border)',
              borderRadius: '6px',
              outline: 'none',
            }}
          >
            {TEMPLATES.map(t => (
              <option key={t.value} value={t.value} style={{ background: 'var(--bg-dark)', color: 'var(--text-main)' }}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={isGenerating || !summaryResult?.summary}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.6rem 1.2rem',
          fontSize: '0.9rem',
          fontWeight: '600',
          background: generated ? '#16a34a' : 'var(--accent-primary)',
          color: '#fff',
          border: 'none',
          borderRadius: '8px',
          cursor: isGenerating || !summaryResult?.summary ? 'not-allowed' : 'pointer',
          opacity: isGenerating || !summaryResult?.summary ? 0.6 : 1,
          transition: 'all 0.2s',
        }}
      >
        {generated ? <FiCheck size={16} /> : <FiFileText size={16} />}
        {isGenerating ? 'Generating...' : generated ? 'Downloaded!' : 'Generate & Download Brief (DOCX)'}
      </button>

      {!summaryResult?.summary && (
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem', marginBottom: 0 }}>
          Upload and summarize a case first to enable brief generation.
        </p>
      )}
    </div>
  );
};

export default BriefGenerator;
