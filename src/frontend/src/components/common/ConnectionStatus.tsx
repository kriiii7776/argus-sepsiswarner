import React from 'react';
import type { ConnectionStatus as ConnectionStatusType } from '../../types';


interface Props {
  status: ConnectionStatusType;
}

export const ConnectionStatus: React.FC<Props> = ({ status }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--text-muted)' }}>Backend (API)</span>
        <span style={{ color: status.backend_connected ? 'var(--color-stable)' : 'var(--color-critical)', fontWeight: 600 }}>
          {status.backend_connected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ color: 'var(--text-muted)' }}>WebSocket Stream</span>
        <span style={{ color: status.websocket_connected ? 'var(--color-stable)' : 'var(--color-critical)', fontWeight: 600 }}>
          {status.websocket_connected ? '● Listening (/ws/stream)' : '○ Offline'}
        </span>
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
