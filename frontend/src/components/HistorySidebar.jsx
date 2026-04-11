import React, { useState, useEffect } from 'react';
import { fetchHistory, searchCases, deleteCase, fetchComparisonHistory } from '../api';
import './HistorySidebar.css';

const HistorySidebar = ({ onSelectCase, onSelectComparison, isOpen, toggleSidebar }) => {
  const [activeTab, setActiveTab] = useState('summaries'); // 'summaries' | 'comparisons'
  const [history, setHistory] = useState([]);
  const [comparisonHistory, setComparisonHistory] = useState([]);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      if (activeTab === 'summaries') {
        loadHistory();
      } else {
        loadComparisonHistory();
      }
    }
  }, [isOpen, activeTab]);

  const loadHistory = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await fetchHistory();
      setHistory(data);
    } catch (err) {
      setError('Failed to load history.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadComparisonHistory = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await fetchComparisonHistory();
      setComparisonHistory(data);
    } catch (err) {
      setError('Failed to load comparison history.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (activeTab === 'comparisons') return; // Only Semantic Search on summaries currently
    
    if (!searchQuery.trim()) {
      loadHistory();
      return;
    }

    setIsLoading(true);
    setError('');
    try {
      const data = await searchCases(searchQuery);
      setHistory(data.results || []);
    } catch (err) {
      setError('Search failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (e, caseId) => {
    e.stopPropagation(); // prevent selecting the case
    if (!window.confirm("Are you sure you want to delete this case?")) return;
    
    try {
      await deleteCase(caseId);
      // Remove from UI immediately
      setHistory(prev => prev.filter(c => c.id !== caseId));
    } catch (err) {
      alert("Failed to delete case.");
    }
  };

  return (
    <div className={`history-sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <h2>History</h2>
        <button className="close-btn" onClick={toggleSidebar}>&times;</button>
      </div>

      <div style={{ display: 'flex', borderBottom: '1px solid var(--panel-border)', marginBottom: '1rem' }}>
         <button 
           style={{ flex: 1, padding: '0.8rem', background: 'transparent', border: 'none', borderBottom: activeTab === 'summaries' ? '2px solid var(--accent-primary)' : '2px solid transparent', color: activeTab === 'summaries' ? 'var(--accent-primary)' : 'var(--text-muted)', cursor: 'pointer', fontWeight: 'bold' }}
           onClick={() => setActiveTab('summaries')}
         >
           Summaries
         </button>
         <button 
           style={{ flex: 1, padding: '0.8rem', background: 'transparent', border: 'none', borderBottom: activeTab === 'comparisons' ? '2px solid var(--accent-secondary)' : '2px solid transparent', color: activeTab === 'comparisons' ? 'var(--accent-secondary)' : 'var(--text-muted)', cursor: 'pointer', fontWeight: 'bold' }}
           onClick={() => setActiveTab('comparisons')}
         >
           Comparisons
         </button>
      </div>

      {activeTab === 'summaries' && (
        <form className="search-form" onSubmit={handleSearch}>
          <input 
            type="text" 
            placeholder="Semantic search (e.g. 'fraud cases')..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
          <button type="submit" disabled={isLoading}>Search</button>
        </form>
      )}

      {error && <div className="sidebar-error">{error}</div>}

      <div className="history-list">
        {isLoading ? (
          <div className="sidebar-loading">Loading...</div>
        ) : activeTab === 'summaries' ? (
           history.length === 0 ? (
            <div className="sidebar-empty">No cases found.</div>
          ) : (
            history.map(item => (
              <div key={item.id} className="history-item" onClick={() => onSelectCase(item)}>
                <div className="history-item-content">
                  <h4>{item.filename || 'Untitled Case'}</h4>
                  <div className="history-meta">
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                    {item.score && (
                      <span className="match-score">
                        Match: {Math.round(item.score * 100)}%
                      </span>
                    )}
                  </div>
                </div>
                <button 
                  className="delete-btn" 
                  onClick={(e) => handleDelete(e, item.id)}
                  title="Delete Case"
                >
                  🗑️
                </button>
              </div>
            ))
          )
        ) : (
           comparisonHistory.length === 0 ? (
             <div className="sidebar-empty">No comparisons found.</div>
           ) : (
             comparisonHistory.map(item => (
               <div key={item.id} className="history-item" onClick={() => onSelectComparison(item)}>
                 <div className="history-item-content">
                   <h4 style={{ fontSize: '0.9rem', marginBottom: '4px' }}>{item.filename1}</h4>
                   <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>vs {item.filename2}</h4>
                   <div className="history-meta">
                     <span>{new Date(item.created_at).toLocaleDateString()}</span>
                   </div>
                 </div>
               </div>
             ))
           )
        )}
      </div>
    </div>
  );
};

export default HistorySidebar;
