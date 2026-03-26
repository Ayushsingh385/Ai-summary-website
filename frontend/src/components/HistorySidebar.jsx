import React, { useState, useEffect } from 'react';
import { fetchHistory, searchCases, deleteCase } from '../api';
import './HistorySidebar.css';

const HistorySidebar = ({ onSelectCase, isOpen, toggleSidebar }) => {
  const [history, setHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadHistory();
    }
  }, [isOpen]);

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

  const handleSearch = async (e) => {
    e.preventDefault();
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
        <h2>Case History & Search</h2>
        <button className="close-btn" onClick={toggleSidebar}>&times;</button>
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <input 
          type="text" 
          placeholder="Semantic search (e.g. 'fraud cases')..." 
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        <button type="submit" disabled={isLoading}>Search</button>
      </form>

      {error && <div className="sidebar-error">{error}</div>}

      <div className="history-list">
        {isLoading ? (
          <div className="sidebar-loading">Loading...</div>
        ) : history.length === 0 ? (
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
        )}
      </div>
    </div>
  );
};

export default HistorySidebar;
