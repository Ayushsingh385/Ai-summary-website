import { FiCalendar, FiDollarSign, FiBook, FiAlertCircle, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { useState } from 'react';

const LegalAnalysis = ({ analysis }) => {
  const [expandedSection, setExpandedSection] = useState('issues');

  if (!analysis) return null;

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="glass-panel" style={{ marginTop: '1.5rem', padding: '1rem' }}>
      <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <FiBook /> Legal Analysis
      </h3>

      {/* Legal Issues */}
      {analysis.legal_issues && analysis.legal_issues.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ color: 'var(--text-main)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiAlertCircle style={{ color: 'var(--accent-primary)' }} />
            Key Legal Issues
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {analysis.legal_issues.map((issue, i) => (
              <div key={i} style={{
                padding: '0.75rem 1rem',
                background: 'var(--bg-card)',
                borderRadius: '8px',
                borderLeft: '3px solid var(--accent-primary)'
              }}>
                <span style={{ color: 'var(--text-main)' }}>{issue.issue}</span>
                {issue.type === 'inferred' && (
                  <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    (inferred)
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timeline */}
      {analysis.timeline && analysis.timeline.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ color: 'var(--text-main)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiCalendar style={{ color: '#22c55e' }} />
            Case Timeline
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {analysis.timeline.slice(0, 10).map((event, i) => (
              <div key={i} style={{
                display: 'flex',
                gap: '1rem',
                alignItems: 'flex-start',
                padding: '0.5rem 0'
              }}>
                <div style={{
                  minWidth: '120px',
                  fontSize: '0.85rem',
                  fontWeight: '600',
                  color: '#22c55e'
                }}>
                  {event.date}
                </div>
                <div style={{
                  color: 'var(--text-muted)',
                  fontSize: '0.9rem',
                  flex: 1
                }}>
                  {event.event.length > 200 ? event.event.slice(0, 200) + '...' : event.event}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monetary Claims */}
      {analysis.monetary_claims && analysis.monetary_claims.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ color: 'var(--text-main)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FiDollarSign style={{ color: '#eab308' }} />
            Monetary Amounts
          </h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {analysis.monetary_claims.map((item, i) => (
              <div key={i} style={{
                padding: '0.5rem 1rem',
                background: 'var(--bg-card)',
                borderRadius: '6px',
                border: '1px solid var(--panel-border)'
              }}>
                <span style={{ fontWeight: '600', color: '#eab308' }}>{item.amount}</span>
                <span style={{
                  marginLeft: '0.5rem',
                  fontSize: '0.75rem',
                  padding: '0.15rem 0.5rem',
                  borderRadius: '4px',
                  background: item.type === 'bribe' ? '#dc262620' :
                             item.type === 'fine' ? '#f59e0b20' :
                             item.type === 'compensation' ? '#22c55e20' : 'var(--bg-card)',
                  color: item.type === 'bribe' ? '#f87171' :
                         item.type === 'fine' ? '#fbbf24' :
                         item.type === 'compensation' ? '#4ade80' : 'var(--text-muted)'
                }}>
                  {item.type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section-wise Analysis */}
      {analysis.sections && Object.keys(analysis.sections).length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <h4 style={{ color: 'var(--text-main)', marginBottom: '0.75rem' }}>
            Document Structure
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {Object.entries(analysis.sections).map(([section, content]) => (
              <div key={section} style={{
                background: 'var(--bg-card)',
                borderRadius: '8px',
                overflow: 'hidden'
              }}>
                <button
                  onClick={() => toggleSection(section)}
                  style={{
                    width: '100%',
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-main)',
                    fontWeight: '600',
                    textTransform: 'capitalize'
                  }}
                >
                  <span style={{ textTransform: 'capitalize' }}>
                    {section.replace('_', ' ')}
                  </span>
                  {expandedSection === section ? <FiChevronUp /> : <FiChevronDown />}
                </button>
                {expandedSection === section && (
                  <div style={{
                    padding: '0.75rem 1rem',
                    paddingTop: 0,
                    color: 'var(--text-muted)',
                    fontSize: '0.9rem',
                    lineHeight: '1.6',
                    maxHeight: '200px',
                    overflowY: 'auto'
                  }}>
                    {content}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No data message */}
      {(!analysis.legal_issues?.length && !analysis.timeline?.length && !analysis.monetary_claims?.length) && (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
          No structured legal data could be extracted from this document.
        </div>
      )}
    </div>
  );
};

export default LegalAnalysis;