import { useState, useEffect } from 'react';
import { uploadPdf, summarizeText, extractKeywords, downloadSummary, downloadOriginalCase, saveCase, fetchProfile } from './api';

import Header from './components/Header';
import FileUpload from './components/FileUpload';
import SummaryOptions from './components/SummaryOptions';
import ResultsPanel from './components/ResultsPanel';
import DownloadBar from './components/DownloadBar';
import LoadingSpinner from './components/LoadingSpinner';
import HistorySidebar from './components/HistorySidebar';
import AuthPage from './components/AuthPage';
import ChatBot from './components/ChatBot';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [userProfile, setUserProfile] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');

  const [loadingMsg, setLoadingMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchProfile()
        .then(data => setUserProfile(data))
        .catch(err => {
          console.error("Failed to fetch profile", err);
          if (err.response && err.response.status === 401) handleLogout();
        });
    }
  }, [isAuthenticated]);
  
  // Sidebar State
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  // Document State
  const [originalText, setOriginalText] = useState('');
  const [filename, setFilename] = useState('');
  const [summaryResult, setSummaryResult] = useState(null);
  const [keywords, setKeywords] = useState([]);
  
  // UI State
  const [selectedLength, setSelectedLength] = useState('medium');
  const [isDownloading, setIsDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  const resetState = () => {
    setOriginalText('');
    setFilename('');
    setSummaryResult(null);
    setKeywords([]);
    setErrorMsg('');
    setActiveTab('summary');
  };

  const handleFileUpload = async (file) => {
    resetState();
    setLoadingMsg('Extracting text from Case File...');
    
    try {
      // 1. Upload & Extract
      const uploadRes = await uploadPdf(file);
      setOriginalText(uploadRes.text);
      setFilename(uploadRes.filename || file.name);
      
      // 2. Extract Keywords (Parallel with summarization)
      setLoadingMsg('Analyzing legal entities...');
      const keywordsRes = await extractKeywords(uploadRes.text).catch(err => {
        console.warn("Keywords error:", err);
        return { keywords: [] };
      });
      setKeywords(keywordsRes.keywords);
      
      // 3. Summarize
      await handleSummarize(uploadRes.text, selectedLength, uploadRes.filename || file.name, keywordsRes.keywords);
      
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error processing file.');
    } finally {
      setLoadingMsg('');
    }
  };

  const handleSummarize = async (textToSummarize, lengthOption, currentFilename = filename, currentKeywords = keywords) => {
    if (!textToSummarize) return;
    
    setLoadingMsg(
      'Generating abstractive summary...\n(This utilizes an AI model and may take a few moments)'
    );
    try {
      const result = await summarizeText(textToSummarize, lengthOption);
      setSummaryResult(result);
      
      // Background save for RAG
      if (currentFilename && currentKeywords) {
        saveCase(
          currentFilename,
          textToSummarize,
          result.summary,
          currentKeywords,
          result.original_stats || {}
        ).catch(err => console.warn('Background save to DB failed:', err));
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Error generating summary.');
    } finally {
      setLoadingMsg('');
    }
  };

  const onSelectCaseFromHistory = (caseItem) => {
    setOriginalText(caseItem.original_text || "");
    setFilename(caseItem.filename || "");
    setKeywords(caseItem.keywords || []);
    
    setSummaryResult({
      summary: caseItem.summary_text || "",
      original_word_count: caseItem.stats?.original_word_count || 0,
      summary_word_count: caseItem.stats?.summary_word_count || 0,
      original_stats: caseItem.stats || {}
    });
    
    setIsSidebarOpen(false); // Close sidebar automatically on mobile/etc
  };

  const onLengthChange = (length) => {
    setSelectedLength(length);
    // Automatically re-summarize if we already have text
    if (originalText) {
      handleSummarize(originalText, length);
    }
  };

  const handleDownload = async (format, docType) => {
    setIsDownloading(true);
    try {
      if (docType === 'original') {
        if (!originalText) return;
        await downloadOriginalCase(originalText, summaryResult?.original_word_count || 0);
      } else {
        if (!summaryResult) return;
        await downloadSummary(
          summaryResult.summary,
          summaryResult.original_word_count,
          summaryResult.summary_word_count,
          format
        );
      }
    } catch (err) {
      setErrorMsg('Error downloading file.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleLogin = (token) => {
    localStorage.setItem('token', token);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    resetState();
  };

  if (!isAuthenticated) {
    return <AuthPage onLogin={handleLogin} />;
  }

  return (
    <div className="container">
      {loadingMsg && <LoadingSpinner message={loadingMsg} />}
      
      <HistorySidebar 
        isOpen={isSidebarOpen} 
        toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        onSelectCase={onSelectCaseFromHistory} 
      />

      <Header 
        onOpenHistory={() => setIsSidebarOpen(true)} 
        onLogout={handleLogout} 
        userProfile={userProfile}
        theme={theme}
        toggleTheme={toggleTheme}
      />

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
              activeTab={activeTab}
              setActiveTab={setActiveTab}
            />

            {(summaryResult || originalText) && (
              <DownloadBar 
                onDownload={handleDownload} 
                isDownloading={isDownloading} 
                disabled={!!loadingMsg}
                activeTab={activeTab}
              />
            )}
          </div>
        )}
      </main>

      <ChatBot documentText={originalText} keywords={keywords} />
    </div>
  );
}

export default App;
