import { useState, useRef, useCallback } from 'react';
import { FiUpload, FiFile, FiCheckCircle, FiXCircle, FiLoader, FiDownload, FiExternalLink } from 'react-icons/fi';

const BatchUpload = ({ onBatchComplete, onSelectFile, initialFiles = [], onFilesChange }) => {
  const [files, setFilesState] = useState(
    initialFiles.length > 0 ? initialFiles : []
  );

  // Sync files state to parent whenever it changes
  const updateFiles = useCallback((updater) => {
    setFilesState(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater;
      if (onFilesChange) onFilesChange(next);
      return next;
    });
  }, [onFilesChange]);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef();

  const handleFileSelect = useCallback((e) => {
    const selected = Array.from(e.target.files);
    if (!selected.length) return;

    const newFiles = selected.map((file, idx) => ({
      file,
      id: `batch-${Date.now()}-${idx}`,
      status: 'pending',
      result: null,
      error: null,
    }));

    updateFiles(prev => [...prev, ...newFiles]);
    e.target.value = '';
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files);
    if (!dropped.length) return;

    const newFiles = dropped.map((file, idx) => ({
      file,
      id: `batch-${Date.now()}-${idx}`,
      status: 'pending',
      result: null,
      error: null,
    }));

    updateFiles(prev => [...prev, ...newFiles]);
  }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const removeFile = (id) => {
    updateFiles(prev => prev.filter(f => f.id !== id));
  };

  const processAll = async () => {
    let pending = files.filter(f => f.status === 'pending');
    if (!pending.length) return;

    setIsUploading(true);

    // Process files one by one through /api/batch_process (text + summary + keywords + save)
    for (const fileObj of pending) {
      setIsUploading(true);

      try {
        updateFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'processing' } : f));

        const token = localStorage.getItem('token');
        const formData = new FormData();
        formData.append('file', fileObj.file);

        const response = await fetch('http://localhost:8000/api/batch_process', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP ${response.status}`);
        }

        const result = await response.json();
        updateFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'done', result } : f));
      } catch (err) {
        updateFiles(prev => prev.map(f => f.id === fileObj.id ? { ...f, status: 'error', error: err.message } : f));
      }
    }

    setIsUploading(false);
  };

  const downloadAllSummaries = () => {
    const doneFiles = files.filter(f => f.status === 'done' && f.result);
    if (!doneFiles.length) return;

    const lines = [];
    doneFiles.forEach(({ result }) => {
      lines.push(`=== ${result.filename} ===`);
      lines.push('');
      if (result.summary && result.summary.summary) {
        lines.push(`Summary: ${result.summary.summary}`);
      }
      lines.push('');
      if (result.keywords && result.keywords.length > 0) {
        const kwList = result.keywords.map(k => typeof k === 'string' ? k : k.keyword).join(', ');
        lines.push(`Keywords: ${kwList}`);
      }
      if (result.case_type && result.case_type.primary_type) {
        lines.push(`Case Type: ${result.case_type.primary_type}`);
      }
      lines.push('');
      lines.push('');
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch_summaries_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleOpenFile = (fileObj) => {
    if (!fileObj.result || !onSelectFile) return;
    const { result } = fileObj;
    onSelectFile({
      text: result.text,
      filename: result.filename,
      summary: result.summary,
      keywords: result.keywords,
      case_type: result.case_type,
      case_id: result.case_id,
    });
  };

  const pendingCount = files.filter(f => f.status === 'pending').length;
  const doneCount = files.filter(f => f.status === 'done').length;
  const processingCount = files.filter(f => f.status === 'processing').length;
  const errorCount = files.filter(f => f.status === 'error').length;
  const totalProcessed = doneCount + errorCount;

  const clearCompleted = () => {
    updateFiles(prev => prev.filter(f => f.status !== 'done' && f.status !== 'error'));
  };

  return (
    <div style={{ marginBottom: '2rem' }}>
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => inputRef.current?.click()}
        style={{
          border: '2px dashed var(--panel-border)',
          borderRadius: '12px',
          padding: '2rem',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'border-color 0.2s, background 0.2s',
          background: 'var(--bg-card)',
          marginBottom: '1rem',
        }}
        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
        onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--panel-border)'}
      >
        <FiUpload size={32} style={{ color: 'var(--accent-primary)', marginBottom: '0.5rem' }} />
        <p style={{ margin: '0 0 0.25rem', fontWeight: '600', color: 'var(--text-main)' }}>
          Drop multiple PDF files here
        </p>
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          or click to browse — files are processed one at a time
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
      </div>

      {/* Action Bar */}
      {files.length > 0 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <span style={{ color: '#22c55e' }}>{doneCount} done</span>
            {processingCount > 0 && (
              <span style={{ color: '#f59e0b' }}>{processingCount} processing</span>
            )}
            <span style={{ color: '#ef4444' }}>{errorCount} failed</span>
            {pendingCount > 0 && <span>{pendingCount} pending</span>}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {doneCount > 0 && (
              <button
                onClick={downloadAllSummaries}
                className="btn btn-outline"
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}
              >
                <FiDownload size={14} /> Download All Summaries
              </button>
            )}
            {pendingCount > 0 && (
              <button
                onClick={processAll}
                disabled={isUploading}
                className="btn btn-primary"
                style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
              >
                {isUploading ? <><FiLoader size={14} style={{ marginRight: '0.3rem', animation: 'spin 1s linear infinite' }} />Processing...</> : `Process All (${pendingCount})`}
              </button>
            )}
            {(doneCount > 0 || errorCount > 0) && (
              <button
                onClick={clearCompleted}
                className="btn btn-outline"
                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
              >
                Clear done/failed
              </button>
            )}
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {isUploading && totalProcessed > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <div style={{
            height: '4px',
            background: 'var(--panel-border)',
            borderRadius: '4px',
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${(totalProcessed / (totalProcessed + pendingCount)) * 100}%`,
              background: 'var(--accent-primary)',
              transition: 'width 0.3s ease',
            }} />
          </div>
          <p style={{ margin: '0.3rem 0 0', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Processing {totalProcessed} of {totalProcessed + pendingCount} files...
          </p>
        </div>
      )}

      {/* Stats Banner */}
      {doneCount > 0 && !isUploading && (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--panel-border)',
          borderRadius: '8px',
          padding: '0.6rem 1rem',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.8rem',
          color: 'var(--text-main)',
        }}>
          <span style={{ color: '#22c55e' }}>&#10003; {doneCount} files processed</span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span>{doneCount} summaries generated</span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span>Saved to vault</span>
        </div>
      )}

      {/* File List */}
      {files.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: '0.75rem'
        }}>
          {files.map(fileObj => (
            <div
              key={fileObj.id}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--panel-border)',
                borderRadius: '8px',
                padding: '0.75rem',
                display: 'flex',
                gap: '0.6rem',
                alignItems: 'flex-start',
              }}
            >
              <FiFile size={20} style={{ color: 'var(--accent-primary)', flexShrink: 0, marginTop: '2px' }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{
                  margin: '0 0 0.25rem',
                  fontSize: '0.82rem',
                  fontWeight: '500',
                  color: 'var(--text-main)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {fileObj.file.name}
                </p>

                {fileObj.status === 'pending' && (
                  <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Ready to process
                  </p>
                )}

                {fileObj.status === 'processing' && (
                  <p style={{ margin: 0, fontSize: '0.72rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <FiLoader size={12} style={{ animation: 'spin 1s linear infinite' }} /> Extracting + summarizing...
                  </p>
                )}

                {fileObj.status === 'done' && fileObj.result && (
                  <div style={{ fontSize: '0.72rem', color: '#22c55e' }}>
                    <p style={{ margin: '0 0 0.2rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <FiCheckCircle size={12} />
                      {fileObj.result.word_count?.toLocaleString() || fileObj.result.page_count || '?'} words
                      {fileObj.result.summary?.summary_word_count
                        ? ` → ${fileObj.result.summary.summary_word_count} word summary`
                        : ' → summary generated'}
                    </p>

                    {/* Summary preview */}
                    {fileObj.result.summary?.summary && (
                      <p style={{
                        margin: '0.2rem 0',
                        color: 'var(--text-main)',
                        fontSize: '0.7rem',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        lineHeight: '1.4',
                      }}>
                        &quot;{fileObj.result.summary.summary.slice(0, 120)}...&quot;
                      </p>
                    )}

                    {/* Keywords chips */}
                    {fileObj.result.keywords && fileObj.result.keywords.length > 0 && (
                      <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', margin: '0.2rem 0' }}>
                        {fileObj.result.keywords.slice(0, 3).map((kw, i) => {
                          const label = typeof kw === 'string' ? kw : kw.keyword;
                          return (
                            <span key={i} style={{
                              background: 'var(--accent-primary)',
                              color: '#fff',
                              borderRadius: '4px',
                              padding: '0.05rem 0.35rem',
                              fontSize: '0.62rem',
                            }}>
                              {label}
                            </span>
                          );
                        })}
                      </div>
                    )}

                    {/* Case type badge */}
                    {fileObj.result.case_type?.primary_type && (
                      <p style={{ margin: '0.1rem 0 0', color: 'var(--text-muted)', fontSize: '0.68rem' }}>
                        {fileObj.result.case_type.primary_type}
                      </p>
                    )}
                  </div>
                )}

                {fileObj.status === 'error' && (
                  <p style={{ margin: 0, fontSize: '0.72rem', color: '#ef4444' }}>
                    <FiXCircle size={12} style={{ marginRight: '0.2rem' }} />
                    {fileObj.error || 'Processing failed'}
                  </p>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flexShrink: 0 }}>
                {fileObj.status === 'done' && fileObj.result && onSelectFile && (
                  <button
                    onClick={() => handleOpenFile(fileObj)}
                    style={{
                      background: 'none',
                      border: '1px solid var(--panel-border)',
                      color: 'var(--accent-primary)',
                      cursor: 'pointer',
                      padding: '0.15rem 0.4rem',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.2rem',
                    }}
                    title="Open in single file view"
                  >
                    <FiExternalLink size={11} /> Open
                  </button>
                )}
                <button
                  onClick={() => removeFile(fileObj.id)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '0.1rem',
                    display: 'flex',
                  }}
                >
                  <FiXCircle size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BatchUpload;