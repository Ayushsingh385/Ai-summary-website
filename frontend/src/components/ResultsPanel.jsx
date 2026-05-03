import { FiClock, FiFile, FiTag, FiBriefcase, FiBook, FiCopy } from 'react-icons/fi';
import { useState } from 'react';
import LegalAnalysis from './LegalAnalysis';
import TagsEditor from './TagsEditor';

// Case type color mapping
const CASE_TYPE_COLORS = {
  "Criminal": { bg: "#dc2626", text: "#fff" },
  "Civil": { bg: "#2563eb", text: "#fff" },
  "Family": { bg: "#db2777", text: "#fff" },
  "Corporate": { bg: "#7c3aed", text: "#fff" },
  "Constitutional": { bg: "#059669", text: "#fff" },
  "Tax": { bg: "#d97706", text: "#fff" },
  "Labor & Employment": { bg: "#0891b2", text: "#fff" },
  "Land & Revenue": { bg: "#65a30d", text: "#fff" },
  "Intellectual Property": { bg: "#c026d3", text: "#fff" },
  "Environmental": { bg: "#0d9488", text: "#fff" },
  "Misc/Other": { bg: "#6b7280", text: "#fff" },
};

const ResultsPanel = ({ originalText, summaryResult, keywords, citations, caseType, legalAnalysis, activeTab, setActiveTab, caseId, tags, onTagsUpdate }) => {
  const [copied, setCopied] = useState(false);

  const handleCopySummary = () => {
    if (!summaryResult?.summary) return;
    navigator.clipboard.writeText(summaryResult.summary).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="glass-panel" style={{ marginTop: '2rem', padding: '1rem' }}>

      {/* Case Type Badge */}
      {caseType && caseType.primary_type && (
        <div style={{
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          flexWrap: 'wrap'
        }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '20px',
            background: CASE_TYPE_COLORS[caseType.primary_type]?.bg || '#6b7280',
            color: CASE_TYPE_COLORS[caseType.primary_type]?.text || '#fff',
            fontWeight: '600',
            fontSize: '0.9rem'
          }}>
            <FiBriefcase />
            {caseType.primary_type}
          </span>
          {caseType.confidence > 0 && (
            <span style={{
              fontSize: '0.85rem',
              color: 'var(--text-muted)'
            }}>
              {caseType.confidence}% confidence
            </span>
          )}
        </div>
      )}

      {caseId && (
        <TagsEditor caseId={caseId} initialTags={tags || []} onTagsUpdate={onTagsUpdate} />
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem', paddingLeft: '1rem' }}>
        <button
          className={`btn ${activeTab === 'summary' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveTab('summary')}
          style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
        >
          Read the summary
        </button>
        <button
          className={`btn ${activeTab === 'original' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveTab('original')}
          style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
        >
          Read the full text
        </button>
        {legalAnalysis && (
          <button
            className={`btn ${activeTab === 'analysis' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('analysis')}
            style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
          >
            Legal Analysis
          </button>
        )}
      </div>

      <div className="results-grid">
        
        {/* Main Content Area */}
        <div className="result-card">
          <div className="result-header">
            <h3>{activeTab === 'summary' ? 'The Summary' : 'Full Text'}</h3>
            {activeTab === 'summary' && summaryResult && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span className="stats">
                  <FiFile style={{ display: 'inline', marginRight: '4px' }} />
                  {summaryResult.summary_word_count} words
                </span>
                <button
                  onClick={handleCopySummary}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem',
                    padding: '0.3rem 0.6rem',
                    fontSize: '0.8rem',
                    background: copied ? '#16a34a' : 'var(--bg-card)',
                    color: copied ? '#fff' : 'var(--text-muted)',
                    border: '1px solid var(--panel-border)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  title="Copy summary to clipboard"
                >
                  <FiCopy size={13} />
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            )}
          </div>
          
          <div className={`result-content ${activeTab === 'summary' ? 'summary-text' : ''}`}>
            {activeTab === 'summary' ? (
              summaryResult ? summaryResult.summary : 'No summary generated yet.'
            ) : activeTab === 'analysis' ? (
              <LegalAnalysis analysis={legalAnalysis} />
            ) : (
              originalText || 'No text extracted.'
            )}
          </div>
        </div>

        {/* Info & Keywords Area */}
        <div className="result-card">
          <div className="result-header">
            <h3>Facts and key details</h3>
          </div>
          <div className="result-content" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Stats */}
            {summaryResult && (
              <div>
                <h4 style={{ color: 'var(--text-main)', marginBottom: '0.5rem' }}>Some stats</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', color: 'var(--text-muted)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiFile /> Original length: {summaryResult.original_word_count} words
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiClock /> Words removed: {summaryResult.original_word_count - summaryResult.summary_word_count} words
                  </div>
                </div>
              </div>
            )}

            {/* Keywords */}
            {keywords && keywords.length > 0 && (
              <div className="keywords-container">
                <h4 style={{ color: 'var(--text-main)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FiTag /> Names and important words
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                  {keywords.map((kw, i) => (
                    <span key={i} className="keyword-chip">
                      {kw.keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Citations */}
            {citations && citations.length > 0 && (
              <div className="citations-container">
                <h4 style={{ color: 'var(--text-main)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FiFile /> Referenced laws and cases
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {citations.map((cite, i) => (
                    <div key={i} style={{ padding: '0.5rem', background: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--panel-border)' }}>
                      {cite.link ? (
                        <a href={cite.link} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 'bold', color: 'var(--primary)', textDecoration: 'none' }}>
                          {cite.citation}
                        </a>
                      ) : (
                        <span style={{ fontWeight: 'bold', color: 'var(--primary)' }}>{cite.citation}</span>
                      )}
                      <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>({cite.type})</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>

      </div>
    </div>
  );
};

export default ResultsPanel;
