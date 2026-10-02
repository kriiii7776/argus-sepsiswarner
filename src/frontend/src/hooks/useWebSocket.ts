// ---------------------------------------------------------------------------
// ARGUS Custom React Hook for Real-Time WebSocket Telemetry (Phase 7C)
// Provides lifecycle awareness, auto-connection, and patient isolation
// ---------------------------------------------------------------------------

import { useState, useEffect, useCallback } from 'react';
import { wsService } from '../services/websocket';
import type { ConnectionLifecycleState, WebSocketEventEnvelope } from '../services/websocket';

export function useWebSocket(patientId?: string) {
  const [connectionState, setConnectionState] = useState<ConnectionLifecycleState>(wsService.getState());
  const [latestEvent, setLatestEvent] = useState<WebSocketEventEnvelope | null>(null);

  useEffect(() => {
    // 1. Subscribe to Connection Lifecycle State Changes
    const unsubscribeState = wsService.subscribeState((newState) => {
      setConnectionState(newState);
    });

    // 2. Auto-connect if disconnected
    if (!wsService.isConnected() && wsService.getState() === 'DISCONNECTED') {
      wsService.connect();
    }

    // 3. Subscribe to Patient-Isolated Telemetry or Global Stream
    let unsubscribeEvents: () => void;
    if (patientId) {
      unsubscribeEvents = wsService.subscribePatient(patientId, (envelope) => {
        setLatestEvent(envelope);
      });
    } else {
      unsubscribeEvents = wsService.subscribeGlobal((envelope) => {
        setLatestEvent(envelope);
      });
    }

    // 4. Memory Cleanup on Unmount / Patient Switching
    return () => {
      unsubscribeState();
      unsubscribeEvents();
    };
  }, [patientId]);

  const reconnect = useCallback(() => {
    wsService.connect();
  }, []);

  return {
    connectionState,
    isConnected: connectionState === 'CONNECTED',
    latestEvent,
    reconnect
  };
}
