import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ARGUS UI Rendering Exception caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '2.5rem',
          backgroundColor: 'var(--bg-card)',
          borderRadius: 'var(--radius-lg)',
          border: '2px solid var(--color-critical)',
          margin: '2rem auto',
          maxWidth: '800px',
          color: 'var(--text-primary)',
          boxShadow: 'var(--shadow-lg)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem' }}>
            <div style={{
              padding: '0.75rem',
              backgroundColor: 'rgba(231, 76, 60, 0.15)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--color-critical)'
            }}>
              <AlertTriangle size={32} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-critical)', margin: 0 }}>
                {this.props.fallbackTitle || 'Patient Focus UI Rendering Error'}
              </h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                An unhandled rendering exception occurred while preparing patient telemetry views.
              </p>
            </div>
          </div>

          {this.state.error && (
            <div style={{
              backgroundColor: 'var(--bg-app)',
              padding: '1rem',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-color)',
              marginBottom: '1.5rem',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              color: 'var(--color-critical)',
              overflowX: 'auto'
            }}>
              <strong>Error Message:</strong> {this.state.error.message || 'Unknown error'}
            </div>
          )}

          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary"
              onClick={this.handleReset}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.2rem', fontSize: '0.85rem' }}
            >
              <RefreshCw size={16} /> Retry Patient Focus
            </button>
            {this.props.onReset && (
              <button
                className="btn btn-outline"
                onClick={this.props.onReset}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.2rem', fontSize: '0.85rem' }}
              >
                <ArrowLeft size={16} /> Back to Patients Roster
              </button>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
