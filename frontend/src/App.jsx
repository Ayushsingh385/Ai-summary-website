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
import TagsEditor from './components/TagsEditor';
import DocumentVault from './components/DocumentVault';
import BatchUpload from './components/BatchUpload';
import BriefGenerator from './components/BriefGenerator';
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
  const [currentCaseId, setCurrentCaseId] = useState(null);
  const [currentTags, setCurrentTags] = useState([]);
  
  // UI State
  const [appMode, setAppMode] = useState('summarize'); // 'summarize' | 'compare' | 'analytics' | 'vault' | 'batch'
  const [selectedLength, setSelectedLength] = useState('medium');
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [isDownloading, setIsDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [cameFromBatch, setCameFromBatch] = useState(false);
  const [batchFiles, setBatchFiles] = useState([]); // persist across mode switches

  const resetState = () => {
    setOriginalText('');
    setFilename('');
    setSummaryResult(null);
    setKeywords([]);
    setCitations([]);
    setCaseType(null);
    setLegalAnalysis(null);
    setCurrentCaseId(null);
    setCurrentTags([]);
    setErrorMsg('');
    setActiveTab('summary');
  };

  const handleFileUpload = async (file) => {
    resetState();
    setLoadingMsg('Reading your file...');

    try {
      // 1. Upload & Extract — show text immediately
      const uploadRes = await uploadPdf(file);
      setOriginalText(uploadRes.text);
      setFilename(uploadRes.filename || file.name);

      // 2. Fire all analysis + summarization in parallel, update UI as each completes
      setLoadingMsg('Analyzing and summarizing...');

      // Keywords
      extractKeywords(uploadRes.text)
        .then(res => { setKeywords(res.keywords || []); setCitations(res.citations || []); })
        .catch(err => console.warn("Keywords error:", err));

      // Classify
      classifyCase(uploadRes.text)
        .then(res => setCaseType(res))
        .catch(err => console.warn("Classify error:", err));

      // Legal analysis
      analyzeDocument(uploadRes.text)
        .then(res => setLegalAnalysis(res))
        .catch(err => console.warn("Analysis error:", err));

      // Summarize (slowest — await it to clear the loading spinner)
      const summaryRes = await summarizeText(uploadRes.text, selectedLength, selectedLanguage).catch(err => {
        console.warn("Summarize error:", err);
        return null;
      });

      if (summaryRes) {
        setSummaryResult(summaryRes);
        const fname = uploadRes.filename || file.name;
        saveCase(fname, uploadRes.text, summaryRes.summary, keywords, summaryRes.original_stats || {}, [], 'new', caseType)
          .then(res => { if (res.case_id) setCurrentCaseId(res.case_id); })
          .catch(err => console.warn('Background save to DB failed:', err));
      }

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

  const handleSummarize = async (textToSummarize, lengthOption, languageOption = selectedLanguage, currentFilename = filename, currentKeywords = keywords, currentCaseType = null) => {
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
          result.original_stats || {},
          [],
          'new',
          currentCaseType
        ).then(res => {
          if (res.case_id) setCurrentCaseId(res.case_id);
        }).catch(err => console.warn('Background save to DB failed:', err));
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
    setCurrentCaseId(caseItem.id);
    setCurrentTags(caseItem.tags || []);

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
            onClick={() => { setAppMode('summarize'); setHistoricalComparisonData(null); }}
          >
            Read one file
          </button>
          <button
            className={`btn btn-mode ${appMode === 'batch' ? 'active-batch' : ''}`}
            onClick={() => { setAppMode('batch'); }}
          >
            Batch upload
          </button>
          {cameFromBatch && (
            <button
              className="btn btn-outline"
              onClick={() => {
                setAppMode('batch');
                setCameFromBatch(false);
              }}
              style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
            >
              ← Back to batch ({batchFiles.length} files)
            </button>
          )}
          <button
            className={`btn btn-mode ${appMode === 'compare' ? 'active-compare' : ''}`}
            onClick={() => { setAppMode('compare'); setHistoricalComparisonData(null); }}
          >
            Compare two files
          </button>
          <button
            className={`btn btn-mode ${appMode === 'vault' ? 'active-workflow' : ''}`}
            onClick={() => { setAppMode('vault'); }}
          >
            Document Vault
          </button>
        </div>

        {appMode === 'analytics' ? (
          <>
            <button
              className="btn btn-outline"
              onClick={() => setAppMode('summarize')}
              style={{ marginBottom: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              ← Back to file
            </button>
            <AnalyticsDashboard onSelectCase={onSelectCaseFromHistory} />
          </>
        ) : appMode === 'compare' ? (
          <CompareMode selectedLanguage={selectedLanguage} initialHistoricalComparison={historicalComparisonData} />
        ) : appMode === 'batch' ? (
          <BatchUpload
            initialFiles={batchFiles}
            onFilesChange={setBatchFiles}
            onSelectFile={(fileData) => {
              setOriginalText(fileData.text);
              setFilename(fileData.filename);
              setSummaryResult(fileData.summary);
              setKeywords(fileData.keywords);
              setCaseType(fileData.case_type);
              setCurrentCaseId(fileData.case_id);
              setCameFromBatch(true);
              setAppMode('summarize');
            }}
          />
        ) : appMode === 'vault' ? (
          <DocumentVault onSelectCase={(item) => {
            onSelectCaseFromHistory(item);
            setAppMode('summarize');
          }} />
        ) : (
          <>


            {/* Upload & Analytics Section */}
            <section className="no-print" style={{
              marginBottom: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem'
            }}>
              <FileUpload onUpload={handleFileUpload} currentFilename={filename} />

              <div>
                <div
                  className="dropzone analytics"
                  onClick={() => { setAppMode('analytics'); setHistoricalComparisonData(null); }}
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
                  caseId={currentCaseId}
                  tags={currentTags}
                  onTagsUpdate={setCurrentTags}
                />

                {/* Brief Generator */}
                <BriefGenerator
                  originalText={originalText}
                  summaryResult={summaryResult}
                  keywords={keywords}
                  caseType={caseType}
                  legalAnalysis={legalAnalysis}
                  filename={filename}
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
