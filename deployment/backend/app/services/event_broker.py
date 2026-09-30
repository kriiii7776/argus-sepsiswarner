import json
from datetime import datetime, timezone
class LocalEventBroker:
    """Single-process development broker; replace with Redis Pub/Sub for multiple workers."""
    def __init__(self): self.subscribers=set()
    async def publish(self, event_type, patient_id, payload):
        message=json.dumps({'type':event_type,'occurred_at':datetime.now(timezone.utc).isoformat(),'patient_id':patient_id,'payload':payload},default=str)
        for ws in list(self.subscribers):
            try: await ws.send_text(message)
            except Exception: self.subscribers.discard(ws)
broker=LocalEventBroker()
