import logging, uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

def configure_logging(level='INFO'):
    logging.basicConfig(level=level, format='%(asctime)s %(levelname)s %(name)s %(message)s')

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id=request.headers.get('X-Correlation-ID',str(uuid.uuid4()))
        request.state.correlation_id=correlation_id
        response=await call_next(request); response.headers['X-Correlation-ID']=correlation_id
        return response
