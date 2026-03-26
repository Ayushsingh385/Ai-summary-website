import { FiBriefcase, FiClock } from 'react-icons/fi';

const Header = ({ onOpenHistory }) => {
  return (
    <header className="fade-in" style={{ textAlign: 'center', marginBottom: '3rem', position: 'relative' }}>
      {onOpenHistory && (
        <button 
          onClick={onOpenHistory}
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: 'var(--text-main)',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
            e.currentTarget.style.borderColor = 'var(--accent-primary)';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
          }}
        >
          <FiClock /> History
        </button>
      )}

      <h1 style={{ fontSize: '2.5rem', fontWeight: 'bold' }}>
        <FiBriefcase className="text-gradient" style={{ marginRight: '0.5rem', verticalAlign: 'middle', display: 'inline-block' }} />
        <span>Zilla <span className="text-gradient">Parishad</span></span>
      </h1>
      <h2 style={{ fontSize: '1.5rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
        Legal Case Summarizer
      </h2>
      <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)' }}>
        Instant, AI-powered analysis and summarization of legal case files.
      </p>
    </header>
  );
};

export default Header;

