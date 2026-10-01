import { useEffect, useRef, useState, useCallback } from 'react';
import { VitalUpdateMessage } from '../types';

export function useWebSocket(sessionId?: string | null) {
  const [isConnected, setIsConnected] = useState(false);
  const [latestVitalMsg, setLatestVitalMsg] = useState<VitalUpdateMessage | null>(null);
  const [history, setHistory] = useState<VitalUpdateMessage[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const path = sessionId ? `/api/v1/stream/${sessionId}` : '/api/v1/stream';
    const wsUrl = `${protocol}//${host}${path}`;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.message_type === 'vital_update') {
          const msg = data as VitalUpdateMessage;
          setLatestVitalMsg(msg);
          setHistory((prev) => {
            const next = [...prev, msg];
            // Keep last 60 seconds of trajectory history for charts
            return next.slice(-60);
          });
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      // Vite or the API may restart while a demo is running. Reconnect without
      // requiring the operator to refresh the dashboard.
      reconnectTimerRef.current = window.setTimeout(connect, 1500);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      ws.close();
    };

    wsRef.current = ws;
  }, [sessionId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [connect]);

  return { isConnected, latestVitalMsg, history, reconnect: connect };
}
