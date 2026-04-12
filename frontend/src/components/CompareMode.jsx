import React, { useState, useEffect } from 'react';
import { uploadPdf, compareDocuments, saveComparison, downloadComparisonReport } from '../api';
import FileUpload from './FileUpload';
import LoadingSpinner from './LoadingSpinner';
import { FiSave, FiCheckCircle, FiXCircle, FiUsers, FiCalendar, FiMapPin, FiBookOpen, FiDownload, FiFileText, FiChevronDown } from 'react-icons/fi';

const CATEGORY_ICONS = {
  "Persons / Parties": <FiUsers />,
  "Dates": <FiCalendar />,
  "Jurisdictions / Locations": <FiMapPin />,
  "Locations": <FiMapPin />,
  "Laws / Statutes": <FiBookOpen />,
};

const TEMPLATES = [
  { value: '', label: '📄 Plain (Default)' },
  { value: 'zp_official', label: '🏛️ Zilla Parishad Official' },
  { value: 'court_order', label: '⚖️ Court Order Format' },
  { value: 'general', label: '📋 General Administrative' },
];

const CompareMode = ({ selectedLanguage, initialHistoricalComparison }) => {
  const [text1, setText1] = useState('');
  const [text2, setText2] = useState('');
  const [filename1, setFilename1] = useState('');
  const [filename2, setFilename2] = useState('');
  
  const [loadingMsg, setLoadingMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  
  const [comparisonResult, setComparisonResult] = useState(null);
  const [isSaved, setIsSaved] = useState(false);

  // Export state
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (initialHistoricalComparison) {
      setText1(initialHistoricalComparison.text1);
      setText2(initialHistoricalComparison.text2);
      setFilename1(initialHistoricalComparison.filename1);
      setFilename2(initialHistoricalComparison.filename2);
      setComparisonResult({
        comparison_summary: initialHistoricalComparison.comparison_summary,
        similarities: initialHistoricalComparison.similarities || [],
        differences: initialHistoricalComparison.differences || [],
        shared_topics: initialHistoricalComparison.shared_topics || [],
        unique_topics_doc1: initialHistoricalComparison.unique_topics_doc1 || [],
        unique_topics_doc2: initialHistoricalComparison.unique_topics_doc2 || [],
        shared_entities: initialHistoricalComparison.shared_entities || [],
        shared_blocks: initialHistoricalComparison.shared_blocks || []
      });
      setIsSaved(true);
    }
  }, [initialHistoricalComparison]);

  const resetUploads = () => {
    setText1(''); setText2('');
    setFilename1(''); setFilename2('');
    setComparisonResult(null);
    setErrorMsg('');
    setIsSaved(false);
  };

  const handleUploadFile1 = async (file) => {
    setLoadingMsg('Extracting Document 1...');
    try {
      const res = await uploadPdf(file);
      setText1(res.text);
      setFilename1(res.filename || file.name);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error processing Document 1');
    } finally {
      setLoadingMsg('');
    }
  };

  const handleUploadFile2 = async (file) => {
    setLoadingMsg('Extracting Document 2...');
    try {
      const res = await uploadPdf(file);
      setText2(res.text);
      setFilename2(res.filename || file.name);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error processing Document 2');
    } finally {
      setLoadingMsg('');
    }
  };

  const runComparison = async () => {
    if (!text1 || !text2) return;
    setLoadingMsg('Analyzing documents with AI... This may take a moment.');
    try {
      const result = await compareDocuments(text1, text2, selectedLanguage);
      setComparisonResult(result);

      // Auto-save
      try {
        await saveComparison(filename1, filename2, text1, text2, result);
        setIsSaved(true);
      } catch (saveErr) {
        console.warn("Could not save to DB automatically", saveErr);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error during comparison.');
    } finally {
      setLoadingMsg('');
    }
  };

  const handleExportComparison = async () => {
    if (!comparisonResult) return;
    setIsExporting(true);
    try {
      await downloadComparisonReport(
        {
          filename1,
          filename2,
          comparison_summary: comparisonResult.comparison_summary,
          similarities: comparisonResult.similarities,
          differences: comparisonResult.differences,
          shared_blocks: comparisonResult.shared_blocks,
          shared_topics: comparisonResult.shared_topics,
          unique_topics_doc1: comparisonResult.unique_topics_doc1,
          unique_topics_doc2: comparisonResult.unique_topics_doc2,
        },
        selectedTemplate || null
      );
    } catch (err) {
      setErrorMsg('Error exporting comparison report.');
    } finally {
      setIsExporting(false);
    }
  };

  const tagStyle = (color) => ({
    display: 'inline-block',
    padding: '0.25rem 0.6rem',
    borderRadius: '4px',
    fontSize: '0.85rem',
    margin: '0.2rem',
    background: `rgba(${color}, 0.15)`,
    color: `rgb(${color})`,
    border: `1px solid rgba(${color}, 0.3)`
  });

  const currentTemplateLabel = TEMPLATES.find(t => t.value === selectedTemplate)?.label || 'Plain (Default)';

  return (
    <div className="fade-in">
      {loadingMsg && <LoadingSpinner message={loadingMsg} />}
      
      {errorMsg && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', padding: '1rem', borderRadius: '8px', color: '#fca5a5', marginBottom: '2rem', textAlign: 'center' }}>
          {errorMsg}
        </div>
      )}

      {/* Upload Zones */}
      {!comparisonResult && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
          <div>
            <h3 style={{ marginBottom: '1rem', color: 'var(--text-main)', textAlign: 'center' }}>Document 1</h3>
            {text1 ? (
              <div style={{ padding: '2rem', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--success)', textAlign: 'center' }}>
                <span style={{ color: 'var(--success)' }}>✓ Loaded: {filename1}</span>
              </div>
            ) : (
              <FileUpload onUpload={handleUploadFile1} />
            )}
          </div>
          <div>
            <h3 style={{ marginBottom: '1rem', color: 'var(--text-main)', textAlign: 'center' }}>Document 2</h3>
            {text2 ? (
              <div style={{ padding: '2rem', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--success)', textAlign: 'center' }}>
                <span style={{ color: 'var(--success)' }}>✓ Loaded: {filename2}</span>
              </div>
            ) : (
              <FileUpload onUpload={handleUploadFile2} />
            )}
          </div>
        </div>
      )}

      {!comparisonResult && text1 && text2 && (
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <button className="btn" onClick={runComparison}>
            Analyze & Compare
          </button>
        </div>
      )}

      {/* Results */}
      {comparisonResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

          {/* Header Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button onClick={resetUploads} style={{ background: 'transparent', border: '1px solid var(--text-muted)', color: 'var(--text-main)', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>
              Start New Comparison
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{filename1} vs {filename2}</span>
              {isSaved && <span style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><FiSave /> Saved</span>}
            </div>
          </div>

          {/* AI Summary */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--panel-border)', borderRadius: '12px', padding: '2rem' }}>
            <h2 style={{ color: 'var(--accent-primary)', marginBottom: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '0.5rem' }}>AI Case Summaries</h2>
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', color: 'var(--text-main)' }}>
              {comparisonResult.comparison_summary}
            </div>
          </div>

          {/* Similarities */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid rgba(34, 197, 94, 0.3)', borderRadius: '12px', padding: '2rem' }}>
            <h2 style={{ color: '#4ade80', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid rgba(34, 197, 94, 0.2)', paddingBottom: '0.5rem' }}>
              <FiCheckCircle /> Similarities Found
            </h2>

            {comparisonResult.similarities && comparisonResult.similarities.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {comparisonResult.similarities.map((sim, idx) => (
                  <div key={idx} style={{ padding: '1rem', background: 'rgba(34, 197, 94, 0.05)', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.1)' }}>
                    <div style={{ fontWeight: 'bold', color: '#4ade80', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {CATEGORY_ICONS[sim.category] || null} {sim.category}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                      {sim.items.map((item, i) => (
                        <span key={i} style={tagStyle('34, 197, 94')}>{item}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No entity-level similarities found between documents.</p>
            )}

            {/* Shared Topics */}
            {comparisonResult.shared_topics && comparisonResult.shared_topics.length > 0 && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(34, 197, 94, 0.05)', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.1)' }}>
                <div style={{ fontWeight: 'bold', color: '#4ade80', marginBottom: '0.5rem' }}>Shared Topics</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                  {comparisonResult.shared_topics.map((topic, i) => (
                    <span key={i} style={tagStyle('34, 197, 94')}>{topic}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Shared Content Blocks (Identical Phrases) */}
            {comparisonResult.shared_blocks && comparisonResult.shared_blocks.length > 0 && (
              <div style={{ marginTop: '1.5rem', padding: '1.5rem', background: 'rgba(34, 197, 94, 0.08)', borderRadius: '8px', border: '1px dashed rgba(34, 197, 94, 0.3)' }}>
                <div style={{ fontWeight: 'bold', color: '#4ade80', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
                  <FiCheckCircle /> Identical Content Blocks
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                  {comparisonResult.shared_blocks.map((block, i) => (
                    <div key={i} style={{ padding: '0.8rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '0.9rem', borderLeft: '3px solid #4ade80', color: 'var(--text-main)', fontStyle: 'italic' }}>
                      "{block}"
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Differences */}
          <div style={{ background: 'var(--bg-card)', border: '1px solid rgba(251, 146, 60, 0.3)', borderRadius: '12px', padding: '2rem' }}>
            <h2 style={{ color: '#fb923c', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid rgba(251, 146, 60, 0.2)', paddingBottom: '0.5rem' }}>
              <FiXCircle /> Differences Found
            </h2>

            {comparisonResult.differences && comparisonResult.differences.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {comparisonResult.differences.map((diff, idx) => (
                  <div key={idx} style={{ padding: '1rem', background: 'rgba(251, 146, 60, 0.05)', borderRadius: '8px', border: '1px solid rgba(251, 146, 60, 0.1)' }}>
                    <div style={{ fontWeight: 'bold', color: '#fb923c', marginBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {CATEGORY_ICONS[diff.category] || null} {diff.category}
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem', fontWeight: 'bold' }}>Only in Document 1:</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                          {diff.only_in_doc1.length > 0 ? diff.only_in_doc1.map((item, i) => (
                            <span key={i} style={tagStyle('139, 92, 246')}>{item}</span>
                          )) : <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem', fontWeight: 'bold' }}>Only in Document 2:</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                          {diff.only_in_doc2.length > 0 ? diff.only_in_doc2.map((item, i) => (
                            <span key={i} style={tagStyle('56, 189, 248')}>{item}</span>
                          )) : <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No entity-level differences found between documents.</p>
            )}

            {/* Unique Topics */}
            {((comparisonResult.unique_topics_doc1 && comparisonResult.unique_topics_doc1.length > 0) ||
              (comparisonResult.unique_topics_doc2 && comparisonResult.unique_topics_doc2.length > 0)) && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(251, 146, 60, 0.05)', borderRadius: '8px', border: '1px solid rgba(251, 146, 60, 0.1)' }}>
                <div style={{ fontWeight: 'bold', color: '#fb923c', marginBottom: '0.8rem' }}>Unique Topics</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem', fontWeight: 'bold' }}>Only in Document 1:</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                      {comparisonResult.unique_topics_doc1.slice(0, 10).map((t, i) => (
                        <span key={i} style={tagStyle('139, 92, 246')}>{t}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem', fontWeight: 'bold' }}>Only in Document 2:</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                      {comparisonResult.unique_topics_doc2.slice(0, 10).map((t, i) => (
                        <span key={i} style={tagStyle('56, 189, 248')}>{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ── Export Comparison Bar ── */}
          <div className="glass-panel fade-in" style={{
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
          }}>
            <h3 style={{ color: 'var(--text-main)' }}>Export Comparison Report</h3>

            {/* Template selector */}
            <div style={{ position: 'relative', width: '260px' }}>
              <button
                onClick={() => setShowTemplateMenu(!showTemplateMenu)}
                style={{
                  width: '100%',
                  padding: '0.55rem 1rem',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--panel-border)',
                  borderRadius: '8px',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.9rem',
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-secondary)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--panel-border)'}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <FiFileText size={14} style={{ color: 'var(--accent-secondary)' }} />
                  {currentTemplateLabel}
                </span>
                <FiChevronDown size={14} style={{
                  transform: showTemplateMenu ? 'rotate(180deg)' : 'rotate(0)',
                  transition: 'transform 0.2s'
                }} />
              </button>

              {showTemplateMenu && (
                <div style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: 0,
                  right: 0,
                  marginBottom: '4px',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--panel-border)',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  zIndex: 50,
                  boxShadow: '0 -8px 24px rgba(0,0,0,0.3)',
                }}>
                  {TEMPLATES.map(t => (
                    <button
                      key={t.value}
                      onClick={() => { setSelectedTemplate(t.value); setShowTemplateMenu(false); }}
                      style={{
                        width: '100%',
                        padding: '0.6rem 1rem',
                        background: selectedTemplate === t.value ? 'rgba(124, 58, 237, 0.15)' : 'transparent',
                        border: 'none',
                        color: selectedTemplate === t.value ? 'var(--accent-secondary)' : 'var(--text-main)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        fontSize: '0.88rem',
                        borderBottom: '1px solid rgba(255,255,255,0.04)',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'rgba(124, 58, 237, 0.1)'}
                      onMouseLeave={e => e.currentTarget.style.background = selectedTemplate === t.value ? 'rgba(124, 58, 237, 0.15)' : 'transparent'}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                className="btn btn-primary"
                onClick={handleExportComparison}
                disabled={isExporting}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                <FiDownload />
                {isExporting ? 'Exporting...' : 'Download DOCX Report'}
              </button>
            </div>
          </div>

        </div>
      )}
    </div>
  );
};

export default CompareMode;
