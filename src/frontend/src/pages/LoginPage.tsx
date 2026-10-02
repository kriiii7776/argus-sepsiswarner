import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { ActivitySquare, ShieldCheck, UserCheck, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess: (role: 'ADMIN' | 'DOCTOR' | 'NURSE') => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      setError('Please enter a valid User ID or Email.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const session = await login(username, password);
      onLoginSuccess(session.role);
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Check credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (presetUser: string) => {
    setLoading(true);
    setError(null);
    try {
      const session = await login(presetUser, 'demo123');
      onLoginSuccess(session.role);
    } catch (err: any) {
      setError(err.message || 'Authentication error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'var(--bg-dark)',
      padding: '2rem'
    }}>
      <div className="card" style={{
        maxWidth: '440px',
        width: '100%',
        padding: '2.5rem',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
        border: '1px solid var(--border-color)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            backgroundColor: 'rgba(52, 152, 219, 0.15)',
            color: 'var(--color-info)',
            marginBottom: '1rem'
          }}>
            <ActivitySquare size={32} />
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            ARGUS SepsisGuard
          </h1>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            AI-Powered ICU Clinical Alert & Command Center
          </p>
        </div>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(231, 76, 60, 0.15)',
            border: '1px solid var(--color-critical)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-critical)',
            fontSize: '0.85rem',
            marginBottom: '1.25rem'
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              User ID / Email
            </label>
            <div style={{ position: 'relative' }}>
              <User size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="e.g. arun@argus.icu or USER-001"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.65rem 0.75rem 0.65rem 2.4rem',
                  backgroundColor: 'var(--bg-app)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.65rem 0.75rem 0.65rem 2.4rem',
                  backgroundColor: 'var(--bg-app)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{
              padding: '0.75rem',
              fontWeight: 700,
              fontSize: '0.95rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              marginTop: '0.5rem'
            }}
          >
            {loading ? 'Authenticating...' : <>Sign In to Clinical System <ArrowRight size={16} /></>}
          </button>
        </form>

        <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.75rem', textAlign: 'center' }}>
            Quick Demo Role Login
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              className="btn btn-outline"
              onClick={() => handleQuickLogin('admin')}
              disabled={loading}
              style={{ justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.5rem 0.75rem' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <ShieldCheck size={14} color="var(--color-critical)" /> Admin Sarah (ICU Administrator)
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ADMIN</span>
            </button>

            <button
              className="btn btn-outline"
              onClick={() => handleQuickLogin('arun')}
              disabled={loading}
              style={{ justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.5rem 0.75rem' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <UserCheck size={14} color="var(--color-info)" /> Dr. Arun (Attending Physician)
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>DOCTOR</span>
            </button>

            <button
              className="btn btn-outline"
              onClick={() => handleQuickLogin('priya')}
              disabled={loading}
              style={{ justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.5rem 0.75rem' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <UserCheck size={14} color="var(--color-stable)" /> Nurse Priya (ICU Nurse)
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>NURSE</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
