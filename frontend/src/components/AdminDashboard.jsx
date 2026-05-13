import { useState, useEffect } from 'react';
import { fetchAdminStats } from '../api';
import { FiUsers, FiDatabase, FiLayers } from 'react-icons/fi';

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAdminStats()
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.response?.data?.detail || "Failed to load admin stats");
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-main)' }}>Loading System Stats...</div>;
  }

  if (error) {
    return <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--danger)' }}>{error}</div>;
  }

  return (
    <div className="glass-panel" style={{ padding: '2rem', marginTop: '1rem' }}>
      <h2 style={{ marginBottom: '1.5rem', color: 'var(--text-main)', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>
        System Administration
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        
        <div className="option-card" style={{ cursor: 'default', textAlign: 'center' }}>
          <FiDatabase size={32} style={{ color: 'var(--accent-primary)', marginBottom: '1rem' }} />
          <h3>{stats.total_cases_ingested}</h3>
          <p style={{ color: 'var(--text-muted)' }}>Total Documents</p>
        </div>

        <div className="option-card" style={{ cursor: 'default', textAlign: 'center' }}>
          <FiUsers size={32} style={{ color: 'var(--accent-secondary)', marginBottom: '1rem' }} />
          <h3>{stats.total_users}</h3>
          <p style={{ color: 'var(--text-muted)' }}>Registered Users</p>
        </div>

        <div className="option-card" style={{ cursor: 'default', textAlign: 'center' }}>
          <FiLayers size={32} style={{ color: 'var(--accent-tertiary, #10b981)', marginBottom: '1rem' }} />
          <h3>{stats.total_comparisons}</h3>
          <p style={{ color: 'var(--text-muted)' }}>Comparisons Performed</p>
        </div>

      </div>

      <div style={{ background: 'var(--bg-secondary)', padding: '1.5rem', borderRadius: '12px' }}>
        <h3 style={{ marginBottom: '1rem', color: 'var(--text-main)' }}>Recent Users</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', color: 'var(--text-main)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
              <th style={{ padding: '0.5rem' }}>ID</th>
              <th style={{ padding: '0.5rem' }}>Username</th>
              <th style={{ padding: '0.5rem' }}>Role</th>
            </tr>
          </thead>
          <tbody>
            {stats.recent_users.map(user => (
              <tr key={user.id} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '0.5rem' }}>{user.id}</td>
                <td style={{ padding: '0.5rem' }}>{user.user_id}</td>
                <td style={{ padding: '0.5rem' }}>
                  <span style={{ 
                    padding: '0.2rem 0.5rem', 
                    borderRadius: '4px', 
                    fontSize: '0.8rem',
                    background: user.is_admin ? 'rgba(99, 102, 241, 0.2)' : 'rgba(100, 100, 100, 0.2)',
                    color: user.is_admin ? 'var(--accent-primary)' : 'var(--text-muted)'
                  }}>
                    {user.is_admin ? 'Admin' : 'User'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminDashboard;
