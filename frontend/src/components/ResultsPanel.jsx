import { FiClock, FiFile, FiTag } from 'react-icons/fi';

const ResultsPanel = ({ originalText, summaryResult, keywords, citations, activeTab, setActiveTab }) => {

  return (
    <div className="glass-panel" style={{ marginTop: '2rem', padding: '1rem' }}>
      
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
      </div>

      <div className="results-grid">
        
        {/* Main Content Area */}
        <div className="result-card">
          <div className="result-header">
            <h3>{activeTab === 'summary' ? 'The Summary' : 'Full Text'}</h3>
            {activeTab === 'summary' && summaryResult && (
              <span className="stats">
                <FiFile style={{ display: 'inline', marginRight: '4px' }} />
                {summaryResult.summary_word_count} words
              </span>
            )}
          </div>
          
          <div className={`result-content ${activeTab === 'summary' ? 'summary-text' : ''}`}>
            {activeTab === 'summary' ? (
              summaryResult ? summaryResult.summary : 'No summary generated yet.'
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
                    <FiClock /> Shortened by: {summaryResult.compression_ratio}%
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
