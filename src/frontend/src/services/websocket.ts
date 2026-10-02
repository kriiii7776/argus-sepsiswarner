// ---------------------------------------------------------------------------
// ARGUS Canonical WebSocket Service (Phase 7C)
// Connected to src/backend FastAPI WebSocket Endpoint (/api/v1/ws/stream)
// ---------------------------------------------------------------------------

export type ConnectionLifecycleState = 
  | 'CONNECTING' 
  | 'CONNECTED' 
  | 'RECONNECTING' 
  | 'DISCONNECTED' 
  | 'ERROR';

export interface WebSocketEventEnvelope {
  type: 'prediction' | 'alert' | 'pong' | 'error' | string;
  occurred_at: string;
  patient_id?: string;
  payload: any;
}

export type PatientEventListener = (envelope: WebSocketEventEnvelope) => void;
export type StateChangeListener = (state: ConnectionLifecycleState) => void;

function deriveWsUrl(): string {
  try {
    if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_WS_BASE_URL) {
      return import.meta.env.VITE_WS_BASE_URL;
    }
    const apiBase = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) 
      || 'http://localhost:8000/api/v1';

    const wsProtocol = apiBase.startsWith('https') ? 'wss://' : 'ws://';
    const cleanPath = apiBase.replace(/^https?:\/\//, '').replace(/\/+$/, '');
    return `${wsProtocol}${cleanPath}/ws/stream`;
  } catch {
    return 'ws://localhost:8000/api/v1/ws/stream';
  }
}

export class WebSocketService {
  private url: string;
  private ws: WebSocket | null = null;
  private connectionState: ConnectionLifecycleState = 'DISCONNECTED';
  
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private isIntentionallyClosed = false;

  // Event Listeners
  private globalListeners: Set<PatientEventListener> = new Set();
  private patientListeners: Map<string, Set<PatientEventListener>> = new Map();
  private stateListeners: Set<StateChangeListener> = new Set();

  // Deduplication cache (key -> timestamp)
  private processedEvents: Map<string, number> = new Map();

  constructor(url: string = deriveWsUrl()) {
    this.url = url;
  }

  public getUrl(): string {
    return this.url;
  }

  public getState(): ConnectionLifecycleState {
    return this.connectionState;
  }

  public isConnected(): boolean {
    return this.connectionState === 'CONNECTED' && this.ws?.readyState === WebSocket.OPEN;
  }

  // ---------------------------------------------------------------------------
  // Connection Lifecycle Management
  // ---------------------------------------------------------------------------

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.setLifecycleState(this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setLifecycleState('CONNECTED');
        this.startKeepalive();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        this.handleIncomingMessage(event.data);
      };

      this.ws.onerror = (_err: Event) => {
        console.warn('[ARGUS WebSocket] Connection error');
        this.setLifecycleState('ERROR');
      };

      this.ws.onclose = (_event: CloseEvent) => {
        this.stopKeepalive();
        this.ws = null;

        if (!this.isIntentionallyClosed) {
          this.setLifecycleState('DISCONNECTED');
          this.scheduleReconnect();
        } else {
          this.setLifecycleState('DISCONNECTED');
        }
      };
    } catch (err) {
      console.error('[ARGUS WebSocket] Failed to initialize WebSocket:', err);
      this.setLifecycleState('ERROR');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopKeepalive();
    this.cancelReconnect();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setLifecycleState('DISCONNECTED');
  }

  private setLifecycleState(newState: ConnectionLifecycleState): void {
    if (this.connectionState !== newState) {
      this.connectionState = newState;
      this.stateListeners.forEach(listener => {
        try { listener(newState); } catch (e) { console.error('State listener error:', e); }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Reconnection with Exponential Backoff
  // ---------------------------------------------------------------------------

  private scheduleReconnect(): void {
    if (this.isIntentionallyClosed || this.reconnectTimer) return;

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn(`[ARGUS WebSocket] Reached max reconnect attempts (${this.maxReconnectAttempts}). Remaining DISCONNECTED.`);
      this.setLifecycleState('DISCONNECTED');
      return;
    }

    this.reconnectAttempts++;
    // Exponential backoff: 1s, 2s, 4s, 8s, 10s max
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), 10000);
    this.setLifecycleState('RECONNECTING');

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private cancelReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Keepalive Ping / Pong
  // ---------------------------------------------------------------------------

  private startKeepalive(): void {
    this.stopKeepalive();
    this.pingTimer = setInterval(() => {
      if (this.isConnected()) {
        try {
          this.ws?.send(JSON.stringify({ type: 'ping' }));
        } catch (e) {
          console.warn('[ARGUS WebSocket] Ping failed:', e);
        }
      }
    }, 30000); // 30 second ping interval
  }

  private stopKeepalive(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Subscription & Patient-Aware Routing
  // ---------------------------------------------------------------------------

  public subscribeState(listener: StateChangeListener): () => void {
    this.stateListeners.add(listener);
    listener(this.connectionState); // Emit initial state
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  public subscribeGlobal(listener: PatientEventListener): () => void {
    this.globalListeners.add(listener);
    return () => {
      this.globalListeners.delete(listener);
    };
  }

  public subscribePatient(patientId: string, listener: PatientEventListener): () => void {
    if (!this.patientListeners.has(patientId)) {
      this.patientListeners.set(patientId, new Set());
    }
    const set = this.patientListeners.get(patientId)!;
    set.add(listener);

    return () => {
      set.delete(listener);
      if (set.size === 0) {
        this.patientListeners.delete(patientId);
      }
    };
  }

  // Send raw clinical vital event to server over WS
  public sendVitalEvent(eventData: Record<string, any>): void {
    if (!this.isConnected()) {
      throw new Error('WebSocket is not connected');
    }
    this.ws?.send(JSON.stringify(eventData));
  }

  // ---------------------------------------------------------------------------
  // Incoming Message Processing & Deduplication
  // ---------------------------------------------------------------------------

  private handleIncomingMessage(data: string): void {
    if (!data || !data.trim()) return;

    let envelope: WebSocketEventEnvelope;
    try {
      envelope = JSON.parse(data);
    } catch {
      console.warn('[ARGUS WebSocket] Received non-JSON message:', data);
      return;
    }

    if (envelope.type === 'pong') {
      return; // Handled keepalive
    }

    if (envelope.type === 'error') {
      console.warn('[ARGUS WebSocket] Server reported error:', envelope.payload || envelope);
    }

    // Deduplication check
    const patientId = envelope.patient_id || envelope.payload?.patient_id;
    const eventTime = envelope.occurred_at || envelope.payload?.prediction_timestamp || new Date().toISOString();
    const dedupKey = `${envelope.type}:${patientId || 'global'}:${eventTime}`;

    const now = Date.now();
    if (this.processedEvents.has(dedupKey)) {
      const prevTime = this.processedEvents.get(dedupKey)!;
      if (now - prevTime < 5000) {
        // Skip duplicate event within 5s window
        return;
      }
    }
    this.processedEvents.set(dedupKey, now);

    // Prune old dedup entries periodically
    if (this.processedEvents.size > 200) {
      for (const [k, t] of this.processedEvents.entries()) {
        if (now - t > 30000) this.processedEvents.delete(k);
      }
    }

    // 1. Dispatch to global listeners
    this.globalListeners.forEach(listener => {
      try { listener(envelope); } catch (e) { console.error('Global listener error:', e); }
    });

    // 2. Dispatch to specific patient subscribers ONLY (Patient Isolation)
    if (patientId && this.patientListeners.has(patientId)) {
      const listeners = this.patientListeners.get(patientId)!;
      listeners.forEach(listener => {
        try { listener(envelope); } catch (e) { console.error(`Patient ${patientId} listener error:`, e); }
      });
    }
  }
}

export const wsService = new WebSocketService();
