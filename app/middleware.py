"""
Middleware components for the FastAPI application.
"""
import json
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils import JSONEncoder

class JSONEncoderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle UUID serialization for responses.
    """
    async def dispatch(self, request: Request, call_next):
        # Process the request and get the response
        response = await call_next(request)
        
        # If the response is a JSONResponse, update the body with our encoder
        if isinstance(response, JSONResponse):
            # Get the original response body as a dict
            body = response.body.decode()
            try:
                # Parse the body
                data = json.loads(body)
                # Re-encode with our custom encoder
                new_body = json.dumps(data, cls=JSONEncoder).encode()
                # Create a new response with the same status code and headers
                return Response(
                    content=new_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            except json.JSONDecodeError:
                # If the body is not valid JSON, just return the original response
                pass
        
        return response 