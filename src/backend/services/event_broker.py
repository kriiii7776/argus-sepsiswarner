import json
from datetime import datetime, timezone
from fastapi import WebSocket

class LocalEventBroker:
    """Single-process development broker; replace with Redis Pub/Sub for multiple workers."""
    def __init__(self):
        self.subscribers: set[WebSocket] = set()

    async def publish(self, event_type: str, patient_id: str | None, payload: dict):
        message = json.dumps({
            'type': event_type,
            'occurred_at': datetime.now(timezone.utc).isoformat(),
            'patient_id': patient_id,
            'payload': payload
        }, default=str)
        
        for ws in list(self.subscribers):
            try:
                await ws.send_text(message)
            except Exception:
                self.subscribers.discard(ws)

broker = LocalEventBroker()
