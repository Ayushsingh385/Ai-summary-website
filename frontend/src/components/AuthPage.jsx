import { useState } from 'react';
import { signUp, signIn } from '../api';

const AuthPage = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [userId, setUserId] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [emailId, setEmailId] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      if (isLogin) {
        const data = await signIn({ user_id: userId, password });
        onLogin(data.access_token);
      } else {
        await signUp({ 
            user_id: userId, 
            employee_id: employeeId, 
            email_id: emailId, 
            password 
        });
        // Auto sign-in or switch to login
        setIsLogin(true);
        setErrorMsg('Sign up successful! Please log in.'); // showing a success message in green would be better, but we can reuse errorMsg for simplicity or create successMsg
        setTimeout(() => setErrorMsg(''), 3000);
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>
          {isLogin ? 'Welcome Back' : 'Create an Account'}
        </h2>
        <p style={styles.subtitle}>
          {isLogin 
            ? 'Sign in to access your PDF summaries' 
            : 'Join to start summarizing cases efficiently'}
        </p>
        
        {errorMsg && (
          <div style={errorMsg.includes('successful') ? styles.successBox : styles.errorBox}>
            {errorMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputGroup}>
            <label style={styles.label}>User ID</label>
            <input 
              type="text" 
              required
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={styles.input}
              placeholder="Enter User ID"
            />
          </div>

          {!isLogin && (
            <>
              <div style={styles.inputGroup}>
                <label style={styles.label}>Employee ID</label>
                <input 
                  type="text" 
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  style={styles.input}
                  placeholder="Enter Employee ID"
                />
              </div>
              <div style={styles.inputGroup}>
                <label style={styles.label}>Email ID</label>
                <input 
                  type="email" 
                  required
                  value={emailId}
                  onChange={(e) => setEmailId(e.target.value)}
                  style={styles.input}
                  placeholder="Enter Email"
                />
              </div>
            </>
          )}

          <div style={styles.inputGroup}>
            <label style={styles.label}>Password</label>
            <input 
              type="password" 
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              placeholder="Enter Password"
            />
          </div>

          <button 
            type="submit" 
            style={{...styles.submitBtn, opacity: loading ? 0.7 : 1}}
            disabled={loading}
          >
            {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <p style={styles.toggleText}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span 
            style={styles.toggleLink} 
            onClick={() => {
                setIsLogin(!isLogin);
                setErrorMsg('');
            }}
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </span>
        </p>
      </div>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #1e1e2f 0%, #151522 100%)',
    fontFamily: '"Inter", sans-serif',
    padding: '1rem'
  },
  card: {
    width: '100%',
    maxWidth: '420px',
    background: 'rgba(255, 255, 255, 0.03)',
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '16px',
    padding: '2.5rem',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
    color: '#fff'
  },
  title: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.75rem',
    fontWeight: '600',
    textAlign: 'center',
    background: 'linear-gradient(90deg, #bb86fc 0%, #3700b3 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent'
  },
  subtitle: {
    margin: '0 0 2rem 0',
    fontSize: '0.9rem',
    color: 'rgba(255, 255, 255, 0.6)',
    textAlign: 'center'
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem'
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem'
  },
  label: {
    fontSize: '0.85rem',
    color: 'rgba(255, 255, 255, 0.8)',
    fontWeight: '500'
  },
  input: {
    padding: '0.8rem 1rem',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(0, 0, 0, 0.2)',
    color: '#fff',
    fontSize: '1rem',
    outline: 'none',
    transition: 'border 0.3s ease'
  },
  submitBtn: {
    marginTop: '1rem',
    padding: '0.85rem',
    borderRadius: '8px',
    border: 'none',
    background: 'linear-gradient(90deg, #bb86fc 0%, #7f39fb 100%)',
    color: '#fff',
    fontSize: '1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease'
  },
  toggleText: {
    marginTop: '1.5rem',
    fontSize: '0.9rem',
    textAlign: 'center',
    color: 'rgba(255, 255, 255, 0.6)'
  },
  toggleLink: {
    color: '#bb86fc',
    cursor: 'pointer',
    fontWeight: '600',
    textDecoration: 'underline'
  },
  errorBox: {
    padding: '0.8rem',
    borderRadius: '8px',
    background: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    marginBottom: '1.5rem',
    fontSize: '0.9rem',
    textAlign: 'center'
  },
  successBox: {
    padding: '0.8rem',
    borderRadius: '8px',
    background: 'rgba(34, 197, 94, 0.1)',
    border: '1px solid rgba(34, 197, 94, 0.3)',
    color: '#86efac',
    marginBottom: '1.5rem',
    fontSize: '0.9rem',
    textAlign: 'center'
  }
};

export default AuthPage;
