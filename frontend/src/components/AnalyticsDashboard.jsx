import React, { useEffect, useState } from 'react';
import { fetchAnalytics, fetchHistory } from '../api';
import './AnalyticsDashboard.css';
import LoadingSpinner from './LoadingSpinner';

const AnalyticsDashboard = ({ onSelectCase }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [recentCases, setRecentCases] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [analyticsResult, historyResult] = await Promise.all([
          fetchAnalytics(),
          fetchHistory()
        ]);
        setData(analyticsResult);
        // Take last 5 cases from history (already sorted newest first)
        setRecentCases(historyResult.slice(0, 5));
      } catch (err) {
        setError('Failed to fetch analytics. Please run the backend server.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  if (loading) return <LoadingSpinner message="Loading advanced analytics..." />;
  if (error) return <div className="analytics-error">{error}</div>;
  if (!data) return null;

  const { total_cases, top_entities, case_types, trends } = data;

  // Max count for scaling the entity bars
  const maxEntityCount = top_entities.length > 0 ? Math.max(...top_entities.map(e => e.count)) : 1;

  // Colors for case types - focused on professional slate/sky shades
  const typeColors = ['#38bdf8', '#0ea5e9', '#0284c7', '#075985', '#0c4a6e'];

  return (
    <div className="analytics-container">
      <div className="analytics-header">
        <h2>Case stats and trends</h2>
        <p>Summary of information from all the files you've uploaded.</p>
      </div>

      {recentCases.length > 0 && (
        <div className="glass-panel" style={{ marginBottom: '1.5rem', padding: '1rem' }}>
          <h3 style={{ marginBottom: '0.75rem', color: 'var(--text-main)' }}>Recent activity</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {recentCases.map((c) => (
              <div
                key={c.id}
                onClick={() => onSelectCase && onSelectCase(c)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.5rem 0.75rem',
                  background: 'var(--bg-card)',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  border: '1px solid var(--panel-border)',
                  transition: 'border-color 0.2s'
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--panel-border)'}
              >
                <span style={{ fontWeight: '500', color: 'var(--text-main)', fontSize: '0.9rem' }}>
                  {c.filename || 'Untitled Case'}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {new Date(c.created_at).toLocaleDateString()} {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="analytics-stats-grid">
        <div className="stat-card glass-panel">
          <h3>Total files</h3>
          <div className="stat-value">{total_cases}</div>
        </div>
        <div className="stat-card glass-panel">
          <h3>Average shortening</h3>
          <div className="stat-value">
            {trends.length > 0 ? Math.round(trends.reduce((acc, curr) => acc + curr.compression_ratio, 0) / trends.length) : 0}%
          </div>
          <p className="stat-sub">Average compression ratio across recent files</p>
        </div>
        <div className="stat-card glass-panel">
          <h3>Most common category</h3>
          <div className="stat-value" style={{color: 'var(--accent-primary)'}}>
            {case_types.length > 0 ? case_types[0].type : "N/A"}
          </div>
        </div>
      </div>

      <div className="analytics-main-grid">
        <div className="analytics-panel glass-panel">
          <h3>Common names, places, and organizations</h3>
          <div className="entity-list">
            {top_entities.length > 0 ? top_entities.map((entity, idx) => (
              <div key={idx} className="entity-item">
                <div className="entity-label">
                  <span className="entity-name">{entity.name}</span>
                  <span className="entity-count">{entity.count}</span>
                </div>
                <div className="entity-bar-bg">
                  <div 
                    className="entity-bar-fill" 
                    style={{ width: `${(entity.count / maxEntityCount) * 100}%` }}
                  ></div>
                </div>
              </div>
            )) : <p>No entity data available yet.</p>}
          </div>
        </div>

        <div className="analytics-panel glass-panel">
          <h3>Category breakdown</h3>
          
          <div className="stacked-bar-container">
            {case_types.map((ctype, idx) => (
              <div 
                key={idx} 
                className="stacked-bar-segment"
                style={{ 
                  width: `${ctype.percentage}%`,
                  backgroundColor: typeColors[idx % typeColors.length]
                }}
                title={`${ctype.type}: ${ctype.percentage}%`}
              ></div>
            ))}
          </div>

          <div className="case-type-legend">
            {case_types.map((ctype, idx) => (
              <div key={idx} className="legend-item">
                <span className="legend-color" style={{ backgroundColor: typeColors[idx % typeColors.length] }}></span>
                <span className="legend-label">{ctype.type}</span>
                <span className="legend-value">{ctype.percentage}%</span>
              </div>
            ))}
            {case_types.length === 0 && <p>No case categories analyzed yet.</p>}
          </div>
        </div>
      </div>

      <div className="analytics-panel glass-panel full-width">
        <h3>How much each file was shortened (recent cases)</h3>
        <div className="trends-container">
          {trends.length > 0 ? trends.map((trend, idx) => (
            <div key={idx} className="trend-row">
              <div className="trend-label">Case #{trend.id} <span className="trend-date">{trend.date}</span></div>
              <div className="trend-bars">
                <div className="trend-bar original-bar" title={`Original: ${trend.original_words} words`}>
                  <span>{trend.original_words}W</span>
                </div>
                <div className="trend-bar summary-bar" style={{ width: `${100 - trend.compression_ratio}%` }} title={`Summary: ${trend.summary_words} words`}>
                   <span>{trend.summary_words}W</span>
                </div>
              </div>
              <div className="trend-efficiency">
                <span className="efficiency-badge">-{trend.compression_ratio}%</span>
              </div>
            </div>
          )) : <p>No trends available. Summarize some cases first.</p>}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
