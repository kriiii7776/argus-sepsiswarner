import React from 'react';
import type { ConnectionStatus as ConnectionStatusType } from '../../types';
import type { ConnectionLifecycleState } from '../../services/websocket';

interface Props {
  status: ConnectionStatusType;
  wsState?: ConnectionLifecycleState;
}

export const ConnectionStatus: React.FC<Props> = ({ status, wsState }) => {
  const getWsBadge = () => {
    switch (wsState) {
      case 'CONNECTED':
        return <span style={{ color: 'var(--color-stable)', fontWeight: 600 }}>🟢 LIVE (/ws/stream)</span>;
      case 'RECONNECTING':
      case 'CONNECTING':
        return <span style={{ color: 'var(--color-watch)', fontWeight: 600 }}>🟡 RECONNECTING</span>;
      case 'ERROR':
        return <span style={{ color: 'var(--color-critical)', fontWeight: 600 }}>⚠ ERROR</span>;
      case 'DISCONNECTED':
      default:
        return <span style={{ color: 'var(--color-critical)', fontWeight: 600 }}>🔴 DISCONNECTED</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--text-muted)' }}>Backend REST API</span>
        <span style={{ color: status.backend_connected ? 'var(--color-stable)' : 'var(--color-critical)', fontWeight: 600 }}>
          {status.backend_connected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--text-muted)' }}>WebSocket Stream</span>
        {getWsBadge()}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--text-muted)' }}>Active Model</span>
        <span style={{ color: 'var(--text-on-dark)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
          {status.active_model}
        </span>
      </div>
    </div>
  );
};
