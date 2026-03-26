import { FiClock, FiFile, FiTag } from 'react-icons/fi';

const ResultsPanel = ({ originalText, summaryResult, keywords, activeTab, setActiveTab }) => {

  return (
    <div className="glass-panel fade-in" style={{ marginTop: '2rem', padding: '1rem' }}>
      
      {/* Tabs */}
      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem', paddingLeft: '1rem' }}>
        <button 
          className={`btn ${activeTab === 'summary' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveTab('summary')}
          style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
        >
          Case Summary
        </button>
        <button 
          className={`btn ${activeTab === 'original' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => setActiveTab('original')}
          style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
        >
          Original Case Text
        </button>
      </div>

      <div className="results-grid">
        
        {/* Main Content Area */}
        <div className="result-card">
          <div className="result-header">
            <h3>{activeTab === 'summary' ? 'Generated Case Summary' : 'Original Case Text'}</h3>
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
            <h3>Case File Intelligence</h3>
          </div>
          <div className="result-content" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Stats */}
            {summaryResult && (
              <div>
                <h4 style={{ color: 'var(--text-main)', marginBottom: '0.5rem' }}>Statistics</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', color: 'var(--text-muted)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiFile /> Original length: {summaryResult.original_word_count} words
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <FiClock /> Compression: -{summaryResult.compression_ratio}%
                  </div>
                </div>
              </div>
            )}

            {/* Keywords */}
            {keywords && keywords.length > 0 && (
              <div className="keywords-container fade-in">
                <h4 style={{ color: 'var(--text-main)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FiTag /> Legal Entities & Key Terms
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

          </div>
        </div>

      </div>
    </div>
  );
};

export default ResultsPanel;
