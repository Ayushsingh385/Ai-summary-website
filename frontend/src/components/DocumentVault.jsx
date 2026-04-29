import { useState, useEffect, useCallback } from 'react';
import { FiSearch, FiFolder } from 'react-icons/fi';
import { fetchHistory, searchCases, deleteCase } from '../api';
import './DocumentVault.css';

const DocumentVault = ({ onSelectCase }) => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const loadAllCases = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchHistory();
      setCases(data);
    } catch (err) {
      setError('Failed to load document vault.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllCases();
  }, []);

  const handleSearch = useCallback(async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) {
      setIsSearching(false);
      loadAllCases();
      return;
    }

    setLoading(true);
    setIsSearching(true);
    setError('');
    
    try {
      const data = await searchCases(searchQuery, 50);
      setCases(data.results || []);
    } catch (err) {
      setError('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  const handleDelete = async (e, caseId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this case? This cannot be undone.')) return;
    try {
      await deleteCase(caseId);
      if (isSearching) {
        handleSearch();
      } else {
        loadAllCases();
      }
    } catch (err) {
      console.warn('Delete failed:', err);
    }
  };

  return (
    <div className="vault-container">
      <div className="vault-header">
        <h2 style={{ margin: 0, fontSize: '1.4rem', color: 'var(--text-main)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
          <FiFolder /> Document Vault
        </h2>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
          Search, filter, and manage all your processed cases in one place.
        </p>
      </div>

      <form onSubmit={handleSearch} className="vault-search-bar">
        <FiSearch className="vault-search-icon" size={18} />
        <input 
          type="text" 
          className="vault-search-input" 
          placeholder="Semantic search by keywords, topics, or parties involved..." 
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" style={{ padding: '0.4rem 1rem' }}>
          Search
        </button>
      </form>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          Loading documents...
        </div>
      ) : error ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--danger)' }}>
          {error}
        </div>
      ) : cases.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          {isSearching ? 'No cases matched your search query.' : 'Your vault is empty. Upload some cases to get started.'}
        </div>
      ) : (
        <>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '-0.5rem' }}>
            Showing {cases.length} result{cases.length !== 1 ? 's' : ''} {isSearching && 'for your query'}
          </div>
          
          <div className="vault-grid">
            {cases.map((item) => (
              <div 
                key={item.id} 
                className="vault-card"
                onClick={() => onSelectCase && onSelectCase(item)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <span className="vault-card-title">{item.filename || 'Untitled Case'}</span>
                </div>

                <div className="vault-card-meta">
                  <span>{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</span>
                  {item.stats?.original_word_count && (
                    <span>{item.stats.original_word_count.toLocaleString()} words</span>
                  )}
                </div>

                {item.case_type?.primary_type && (
                  <div>
                    <span className="vault-card-badge">
                      {item.case_type.primary_type}
                    </span>
                  </div>
                )}

                {item.tags?.length > 0 && (
                  <div className="vault-card-tags">
                    {item.tags.slice(0, 4).map(tag => (
                      <span key={tag} className="vault-tag">{tag}</span>
                    ))}
                    {item.tags.length > 4 && <span className="vault-tag">+{item.tags.length - 4}</span>}
                  </div>
                )}
                
                <div style={{ marginTop: 'auto', textAlign: 'right' }}>
                  <button 
                    onClick={(e) => handleDelete(e, item.id)}
                    style={{ background: 'none', border: 'none', color: 'var(--danger)', fontSize: '0.75rem', cursor: 'pointer', opacity: 0.7 }}
                    onMouseEnter={(e) => e.target.style.opacity = 1}
                    onMouseLeave={(e) => e.target.style.opacity = 0.7}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default DocumentVault;
