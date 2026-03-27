import { useState } from 'react';
import { FiBriefcase, FiClock, FiLogOut, FiUser, FiSun, FiMoon } from 'react-icons/fi';

const Header = ({ onOpenHistory, onLogout, userProfile, theme, toggleTheme }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  return (
    <header className="fade-in" style={{ textAlign: 'center', marginBottom: '3rem', position: 'relative', zIndex: 1000 }}>
      
      {/* Top Left User Menu */}
      {userProfile && (
        <div style={{ position: 'absolute', top: 0, left: 0, textAlign: 'left', zIndex: 100 }}>
          <button 
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'var(--text-main)',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontWeight: '600',
              transition: 'all 0.2s ease'
            }}
          >
            <FiUser /> {userProfile.user_id}
          </button>

          {isMenuOpen && (
            <div className="fade-in" style={{
              position: 'absolute',
              top: '120%',
              left: 0,
              background: 'var(--bg-darker)',
              border: '1px solid var(--panel-border)',
              borderRadius: '8px',
              padding: '1rem',
              width: '260px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
              color: 'var(--text-main)',
              textAlign: 'left',
              zIndex: 9999
            }}>
              <div style={{ marginBottom: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '0.8rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '0.5rem', letterSpacing: '1px' }}>PROFILE</div>
                <div style={{ marginBottom: '0.3rem' }}><strong>User ID:</strong> {userProfile.user_id}</div>
                <div style={{ marginBottom: '0.3rem' }}><strong>Employee ID:</strong> {userProfile.employee_id}</div>
                <div style={{ marginBottom: '0.3rem', wordBreak: 'break-all' }}><strong>Email:</strong> {userProfile.email_id}</div>
              </div>
              
              <div>
                <button 
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleTheme();
                  }}
                  style={{
                    width: '100%',
                    background: 'rgba(139, 92, 246, 0.15)',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                    color: 'var(--text-main)',
                    padding: '0.6rem',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                    fontWeight: '600',
                    transition: 'all 0.2s ease'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = 'rgba(139, 92, 246, 0.25)'}
                  onMouseOut={(e) => e.currentTarget.style.background = 'rgba(139, 92, 246, 0.15)'}
                >
                  {theme === 'dark' ? <><FiSun size={18} /> Switch to Light Mode</> : <><FiMoon size={18} /> Switch to Dark Mode</>}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {onOpenHistory && (
        <button 
          onClick={onOpenHistory}
          style={{
            position: 'absolute',
            top: 0,
            right: 120,
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
      
      {onLogout && (
        <button 
          onClick={onLogout}
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
            e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.5)';
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
            e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.3)';
          }}
        >
          <FiLogOut /> Logout
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

