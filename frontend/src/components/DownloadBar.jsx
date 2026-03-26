import { FiDownload } from 'react-icons/fi';

const DownloadBar = ({ onDownload, isDownloading, disabled, activeTab }) => {
  return (
    <div className="glass-panel fade-in" style={{ 
      marginTop: '2rem', 
      padding: '1.5rem', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center',
      gap: '1rem' 
    }}>
      <h3 style={{ color: 'var(--text-main)' }}>Export Results</h3>
      
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
        {activeTab === 'summary' && (
          <button 
            className="btn btn-outline" 
            onClick={() => onDownload('txt', 'summary')}
            disabled={isDownloading || disabled}
          >
            <FiDownload /> Download TXT
          </button>
        )}
        
        <button 
          className="btn btn-primary" 
          onClick={() => onDownload('pdf', activeTab)}
          disabled={isDownloading || disabled}
        >
          <FiDownload /> 
          {activeTab === 'summary' ? 'Download Case Summary (PDF)' : 'Download Original Case'}
        </button>
      </div>
    </div>
  );
};

export default DownloadBar;
