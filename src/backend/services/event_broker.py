import json
import logging
from datetime import datetime, timezone
from fastapi import WebSocket

log = logging.getLogger('sepsisguard.broker')

class LocalEventBroker:
    """Single-process development broker supporting patient isolation for staff subscribers."""
    def __init__(self):
        self.subscribers: set[WebSocket] = set()

    async def publish(self, event_type: str, patient_id: str | None, payload: dict):
        message = json.dumps({
            'type': event_type,
            'occurred_at': datetime.now(timezone.utc).isoformat(),
            'patient_id': patient_id,
            'payload': payload
        }, default=str)

        from src.backend.services.alert_router import alert_router
        
        for ws in list(self.subscribers):
            try:
                user_id = getattr(getattr(ws, 'state', None), 'user_id', None)
                if patient_id and user_id:
                    # Enforce patient isolation at backend WebSocket broker level
                    if not alert_router.is_user_authorized_for_patient(user_id, patient_id):
                        continue
                await ws.send_text(message)
            except Exception as exc:
                log.debug("WebSocket send error; discarding subscriber: %s", exc)
                self.subscribers.discard(ws)

broker = LocalEventBroker()
