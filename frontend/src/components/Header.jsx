import { useState, useRef, useEffect } from 'react';
import { FiBriefcase, FiClock, FiLogOut, FiUser, FiSun, FiMoon, FiMenu, FiX } from 'react-icons/fi';

const Header = ({ onOpenHistory, onLogout, userProfile, theme, toggleTheme, isSidebarOpen, onOpenAdmin }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const mobileMenuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false);
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target)) {
        setIsMobileMenuOpen(false);
      }
    };
    
    if (isMenuOpen || isMobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen, isMobileMenuOpen]);

  return (
    <header className="app-header">
      {/* Top navigation bar */}
      <nav className="header-nav">
        {/* Left: User menu */}
        {userProfile && (
          <div ref={menuRef} className="header-user-menu">
            <button 
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="header-btn"
            >
              <FiUser /> <span className="header-btn-text">{userProfile.user_id}</span>
            </button>

            {isMenuOpen && (
              <div className="header-dropdown">
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
                    className="header-theme-btn"
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

        {/* Right: Desktop buttons */}
        <div className="header-actions-desktop">
          {onOpenHistory && (
            <button onClick={onOpenHistory} className="header-btn">
              <FiClock /> History
            </button>
          )}
          {userProfile?.is_admin && onOpenAdmin && (
            <button onClick={onOpenAdmin} className="header-btn" style={{ background: 'var(--accent-primary)', color: 'white' }}>
              <FiUser /> Admin Panel
            </button>
          )}
          {onLogout && (
            <button onClick={onLogout} className="header-btn danger">
              <FiLogOut /> Logout
            </button>
          )}
        </div>

        {/* Right: Mobile hamburger */}
        <div className="header-actions-mobile" ref={mobileMenuRef}>
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="header-btn"
            aria-label="Menu"
          >
            {isMobileMenuOpen ? <FiX size={20} /> : <FiMenu size={20} />}
          </button>

          {isMobileMenuOpen && (
            <div className="header-mobile-dropdown">
              {onOpenHistory && (
                <button onClick={() => { onOpenHistory(); setIsMobileMenuOpen(false); }} className="header-mobile-item">
                  <FiClock /> History
                </button>
              )}
              {userProfile?.is_admin && onOpenAdmin && (
                <button onClick={() => { onOpenAdmin(); setIsMobileMenuOpen(false); }} className="header-mobile-item">
                  <FiUser /> Admin Panel
                </button>
              )}
              {onLogout && (
                <button onClick={() => { onLogout(); setIsMobileMenuOpen(false); }} className="header-mobile-item danger">
                  <FiLogOut /> Logout
                </button>
              )}
            </div>
          )}
        </div>
      </nav>

      {/* Title section */}
      <div className="header-title-section">
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
      </div>
    </header>
  );
};

export default Header;
