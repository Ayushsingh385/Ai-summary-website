import { useState, useEffect } from 'react';
import { uploadPdf, summarizeText, extractKeywords, classifyCase, analyzeDocument, downloadSummary, downloadOriginalCase, saveCase, fetchProfile } from './api';

import Header from './components/Header';
import FileUpload from './components/FileUpload';
import SummaryOptions from './components/SummaryOptions';
import ResultsPanel from './components/ResultsPanel';
import DownloadBar from './components/DownloadBar';
import LoadingSpinner from './components/LoadingSpinner';
import HistorySidebar from './components/HistorySidebar';
import AuthPage from './components/AuthPage';
import ChatBot from './components/ChatBot';
import CompareMode from './components/CompareMode';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import LegalAnalysis from './components/LegalAnalysis';
import { FiPieChart } from 'react-icons/fi';

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
  const [citations, setCitations] = useState([]);
  const [caseType, setCaseType] = useState(null);
  const [legalAnalysis, setLegalAnalysis] = useState(null);
  
  // UI State
  const [appMode, setAppMode] = useState('summarize'); // 'summarize' | 'compare' | 'analytics'
  const [selectedLength, setSelectedLength] = useState('medium');
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [isDownloading, setIsDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');

  const resetState = () => {
    setOriginalText('');
    setFilename('');
    setSummaryResult(null);
    setKeywords([]);
    setCitations([]);
    setCaseType(null);
    setLegalAnalysis(null);
    setErrorMsg('');
    setActiveTab('summary');
  };

  const handleFileUpload = async (file) => {
    resetState();
    setLoadingMsg('Reading your file...');

    try {
      // 1. Upload & Extract
      const uploadRes = await uploadPdf(file);
      setOriginalText(uploadRes.text);
      setFilename(uploadRes.filename || file.name);

      // 2. Extract Keywords, Classify Case Type, and Analyze (in parallel)
      setLoadingMsg('Analyzing document...');
      const [keywordsRes, classifyRes, analysisRes] = await Promise.all([
        extractKeywords(uploadRes.text).catch(err => {
          console.warn("Keywords error:", err);
          return { keywords: [], citations: [] };
        }),
        classifyCase(uploadRes.text).catch(err => {
          console.warn("Classify error:", err);
          return null;
        }),
        analyzeDocument(uploadRes.text).catch(err => {
          console.warn("Analysis error:", err);
          return null;
        })
      ]);
      setKeywords(keywordsRes.keywords || []);
      setCitations(keywordsRes.citations || []);
      setCaseType(classifyRes);
      setLegalAnalysis(analysisRes);

      // 3. Summarize
      await handleSummarize(uploadRes.text, selectedLength, uploadRes.filename || file.name, keywordsRes.keywords);

    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = err.message === 'Network Error' 
        ? 'Network Error: Please check if the backend server is running and reachable.' 
        : (detail || err.message || 'Error processing file.');
      setErrorMsg(message);
      console.error("Upload error:", err);
    } finally {
      setLoadingMsg('');
    }
  };

  const handleSummarize = async (textToSummarize, lengthOption, languageOption = selectedLanguage, currentFilename = filename, currentKeywords = keywords) => {
    if (!textToSummarize) return;
    
    setLoadingMsg(
      'Writing your summary now. This might take a few seconds.'
    );
    try {
      const result = await summarizeText(textToSummarize, lengthOption, languageOption);
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

  const onSelectCaseFromHistory = async (caseItem) => {
    setOriginalText(caseItem.original_text || "");
    setFilename(caseItem.filename || "");
    setKeywords(caseItem.keywords || []);
    setCitations([]);

    setSummaryResult({
      summary: caseItem.summary_text || "",
      original_word_count: caseItem.stats?.original_word_count || 0,
      summary_word_count: caseItem.stats?.summary_word_count || 0,
      original_stats: caseItem.stats || {}
    });

    // Classify the case type from history
    if (caseItem.original_text) {
      try {
        const classifyRes = await classifyCase(caseItem.original_text);
        setCaseType(classifyRes);
      } catch (err) {
        console.warn("Classify error from history:", err);
        setCaseType(null);
      }
    }

    setIsSidebarOpen(false);
    setActiveTab('summary');
  };

  const [historicalComparisonData, setHistoricalComparisonData] = useState(null);

  const onSelectComparisonFromHistory = async (comparisonItem) => {
    setIsSidebarOpen(false);
    setAppMode('compare');
    setLoadingMsg('Loading historical comparison...');
    try {
      import('./api').then(async (api) => {
         const data = await api.fetchComparisonDetail(comparisonItem.id);
         setHistoricalComparisonData(data);
         setLoadingMsg('');
      });
    } catch (err) {
      setErrorMsg('Failed to load comparison data');
      setLoadingMsg('');
    }
  };

  const onLengthChange = (length) => {
    setSelectedLength(length);
    // Automatically re-summarize if we already have text
    if (originalText) {
      handleSummarize(originalText, length, selectedLanguage);
    }
  };

  const onLanguageChange = (language) => {
    setSelectedLanguage(language);
    if (originalText) {
      handleSummarize(originalText, selectedLength, language);
    }
  };

  const handleDownload = async (format, docType, template = null) => {
    setIsDownloading(true);
    try {
      if (docType === 'original') {
        if (!originalText) return;
        await downloadOriginalCase(
          originalText,
          summaryResult?.original_word_count || 0,
          format,
          template
        );
      } else {
        if (!summaryResult) return;
        await downloadSummary(
          summaryResult.summary,
          summaryResult.original_word_count,
          summaryResult.summary_word_count,
          format,
          keywords,
          template
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
        onSelectComparison={onSelectComparisonFromHistory}
      />

      <Header 
        onOpenHistory={() => setIsSidebarOpen(true)} 
        onLogout={handleLogout} 
        userProfile={userProfile}
        theme={theme}
        toggleTheme={toggleTheme}
        isSidebarOpen={isSidebarOpen}
      />

      {/* Sidebar Backdrop Overlay */}
      {isSidebarOpen && (
        <div 
          onClick={() => setIsSidebarOpen(false)}
          className=""
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.7)', /* Solid dark overlay */
            zIndex: 1500,
            cursor: 'pointer'
          }}
        />
      )}

      <main>
        {/* Mode Toggle */}
        <div className="no-print" style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <button 
            className={`btn btn-mode ${appMode === 'summarize' ? 'active-summarize' : ''}`} 
            onClick={() => { resetState(); setAppMode('summarize'); setHistoricalComparisonData(null); }}
          >
            Read one file
          </button>
          <button 
            className={`btn btn-mode ${appMode === 'compare' ? 'active-compare' : ''}`} 
            onClick={() => { resetState(); setAppMode('compare'); setHistoricalComparisonData(null); }}
          >
            Compare two files
          </button>
        </div>

        {appMode === 'analytics' ? (
          <AnalyticsDashboard />
        ) : appMode === 'compare' ? (
          <CompareMode selectedLanguage={selectedLanguage} initialHistoricalComparison={historicalComparisonData} />
        ) : (
          <>
            {/* Upload & Analytics Section */}
            <section className="no-print" style={{ 
              marginBottom: '1rem', 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '1rem'
            }}>
              <FileUpload onUpload={handleFileUpload} />
              
              <div>
                <div 
                  className="dropzone analytics"
                  onClick={() => { resetState(); setAppMode('analytics'); setHistoricalComparisonData(null); }}
                  style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', minHeight: '110px' }}
                >
                  <FiPieChart className="dropzone-icon" />
                  <h3>Case stats and trends</h3>
                  <p>See common names, dates, and patterns across all your uploads.</p>
                </div>
              </div>
            </section>

            {/* Error Handling */}
            {errorMsg && (
              <div style={{
                background: '#451a1a', 
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
              <div>
                <h3 className="no-print" style={{ textAlign: 'center', marginBottom: '1rem' }}>How detailed should the summary be?</h3>
                <SummaryOptions 
                  selectedLength={selectedLength} 
                  onSelect={onLengthChange} 
                  selectedLanguage={selectedLanguage}
                  onLanguageChange={onLanguageChange}
                />
                
                <ResultsPanel
                  originalText={originalText}
                  summaryResult={summaryResult}
                  keywords={keywords}
                  citations={citations}
                  caseType={caseType}
                  legalAnalysis={legalAnalysis}
                  activeTab={activeTab}
                  setActiveTab={setActiveTab}
                />

                {(summaryResult || originalText) && (
                  <div className="no-print">
                    <DownloadBar 
                      onDownload={handleDownload} 
                      isDownloading={isDownloading} 
                      disabled={!!loadingMsg}
                      activeTab={activeTab}
                    />
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>

      <div className="no-print">
        <ChatBot documentText={originalText} keywords={keywords} />
      </div>
    </div>
  );
}

export default App;
