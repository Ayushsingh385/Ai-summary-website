import { useState, useRef, useEffect } from 'react';
import { FiBriefcase, FiClock, FiLogOut, FiUser, FiSun, FiMoon } from 'react-icons/fi';

const Header = ({ onOpenHistory, onLogout, userProfile, theme, toggleTheme, isSidebarOpen }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false);
      }
    };
    
    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen]);

  return (
    <header style={{ 
      textAlign: 'center', 
      marginBottom: '3rem', 
      position: 'relative', 
      zIndex: 1000,
      opacity: 1,
      transition: 'all 0.3s ease',
    }}>
      
      {/* Top Left User Menu */}
      {userProfile && (
        <div ref={menuRef} style={{ position: 'absolute', top: 0, left: 0, textAlign: 'left', zIndex: 100 }}>
          <button 
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="header-btn"
          >
            <FiUser /> {userProfile.user_id}
          </button>

          {isMenuOpen && (
            <div style={{
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
                    background: 'var(--bg-dark)',
                    border: '1px solid var(--panel-border)',
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
                  onMouseOver={(e) => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                  onMouseOut={(e) => e.currentTarget.style.borderColor = 'var(--panel-border)'}
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
          className="header-btn"
          style={{
            position: 'absolute',
            top: 0,
            right: 120,
          }}
        >
          <FiClock /> History
        </button>
      )}
      
      {onLogout && (
        <button 
          onClick={onLogout}
          className="header-btn danger"
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
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
        Legal help for long documents
      </h2>
      <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)' }}>
        Upload your legal files and we'll give you a summary of the facts and key details in seconds.
      </p>
    </header>
  );
};

export default Header;

