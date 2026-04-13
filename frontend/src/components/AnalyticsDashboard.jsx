import React, { useEffect, useState } from 'react';
import { fetchAnalytics } from '../api';
import './AnalyticsDashboard.css';
import LoadingSpinner from './LoadingSpinner';

const AnalyticsDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchAnalytics();
        setData(result);
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

  // Colors for case types pie/stacked bar
  const typeColors = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

  return (
    <div className="analytics-container fade-in">
      <div className="analytics-header">
        <h2>Advanced Analytics Dashboard</h2>
        <p>Insights automatically derived from your document history using NLP.</p>
      </div>

      <div className="analytics-stats-grid">
        <div className="stat-card glass-panel">
          <h3>Total Documents Processed</h3>
          <div className="stat-value">{total_cases}</div>
        </div>
        <div className="stat-card glass-panel">
          <h3>Overall Time Saved</h3>
          <div className="stat-value text-gradient">
            {trends.length > 0 ? Math.round(trends.reduce((acc, curr) => acc + curr.compression_ratio, 0) / trends.length) : 0}%
          </div>
          <p className="stat-sub">Average compression ratio across recent files</p>
        </div>
        <div className="stat-card glass-panel">
          <h3>Most Common Type</h3>
          <div className="stat-value" style={{color: 'var(--accent-secondary)'}}>
            {case_types.length > 0 ? case_types[0].type : "N/A"}
          </div>
        </div>
      </div>

      <div className="analytics-main-grid">
        <div className="analytics-panel glass-panel">
          <h3>Top extracted Entities (Names, Orgs, Locations)</h3>
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
          <h3>Case Category Distribution</h3>
          
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
        <h3>Summary Length Efficiency Trends (Recent Cases)</h3>
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
