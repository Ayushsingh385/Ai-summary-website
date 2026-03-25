import { FiBriefcase } from 'react-icons/fi';

const Header = () => {
  return (
    <header className="fade-in" style={{ textAlign: 'center', marginBottom: '3rem' }}>
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
