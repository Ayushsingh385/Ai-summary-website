import { useState } from 'react';
import { uploadPdf, summarizeText, extractKeywords, downloadSummary } from './api';

import Header from './components/Header';
import FileUpload from './components/FileUpload';
import SummaryOptions from './components/SummaryOptions';
import ResultsPanel from './components/ResultsPanel';
import DownloadBar from './components/DownloadBar';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const [loadingMsg, setLoadingMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  
  // Document State
  const [originalText, setOriginalText] = useState('');
  const [summaryResult, setSummaryResult] = useState(null);
  const [keywords, setKeywords] = useState([]);
  
  // UI State
  const [selectedLength, setSelectedLength] = useState('medium');
  const [isDownloading, setIsDownloading] = useState(false);

  const resetState = () => {
    setOriginalText('');
    setSummaryResult(null);
    setKeywords([]);
    setErrorMsg('');
  };

  const handleFileUpload = async (file) => {
    resetState();
    setLoadingMsg('Extracting text from Case File...');
    
    try {
      // 1. Upload & Extract
      const uploadRes = await uploadPdf(file);
      setOriginalText(uploadRes.text);
      
      // 2. Extract Keywords (Parallel with summarization)
      setLoadingMsg('Analyzing legal entities...');
      const keywordsRes = await extractKeywords(uploadRes.text).catch(err => {
        console.warn("Keywords error:", err);
        return { keywords: [] };
      });
      setKeywords(keywordsRes.keywords);
      
      // 3. Summarize
      await handleSummarize(uploadRes.text, selectedLength);
      
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error processing file.');
    } finally {
      setLoadingMsg('');
    }
  };

  const handleSummarize = async (textToSummarize, lengthOption) => {
    if (!textToSummarize) return;
    
    setLoadingMsg(
      'Generating abstractive summary...\n(This utilizes an AI model and may take a few moments)'
    );
    try {
      const result = await summarizeText(textToSummarize, lengthOption);
      setSummaryResult(result);
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error generating summary.');
    } finally {
      setLoadingMsg('');
    }
  };

  const onLengthChange = (length) => {
    setSelectedLength(length);
    // Automatically re-summarize if we already have text
    if (originalText) {
      handleSummarize(originalText, length);
    }
  };

  const handleDownload = async (format) => {
    if (!summaryResult) return;
    setIsDownloading(true);
    try {
      await downloadSummary(
        summaryResult.summary,
        summaryResult.original_word_count,
        summaryResult.summary_word_count,
        format
      );
    } catch (err) {
      setErrorMsg('Error downloading file.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="container">
      {loadingMsg && <LoadingSpinner message={loadingMsg} />}
      
      <Header />

      <main>
        {/* Upload Section */}
        <section style={{ marginBottom: '3rem' }}>
          <FileUpload onUpload={handleFileUpload} />
        </section>

        {/* Error Handling */}
        {errorMsg && (
          <div className="fade-in" style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--danger)',
            padding: '1rem',
            borderRadius: '8px',
            color: '#fca5a5',
            marginBottom: '2rem',
            textAlign: 'center'
          }}>
            {errorMsg}
          </div>
        )}

        {/* Main Content Areas */}
        {originalText && (
          <div className="fade-in">
            <h3 style={{ textAlign: 'center', marginBottom: '1rem' }}>Customize Case Summary Length</h3>
            <SummaryOptions 
              selectedLength={selectedLength} 
              onSelect={onLengthChange} 
            />
            
            <ResultsPanel 
              originalText={originalText}
              summaryResult={summaryResult}
              keywords={keywords}
            />

            {summaryResult && (
              <DownloadBar 
                onDownload={handleDownload} 
                isDownloading={isDownloading} 
                disabled={!!loadingMsg}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
