"""
JWT Authentication middleware for the MCP Server.
Validates Bearer tokens using the same JWT config as the FastAPI auth layer.
Stores the authenticated user_id in a context variable for tool functions to use.
"""
import contextvars
import logging

from jose import JWTError, jwt
from django.conf import settings

logger = logging.getLogger(__name__)

# Context variable to hold the authenticated user's ID throughout the request lifecycle
authenticated_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    'authenticated_user_id', default=None
)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"


def verify_jwt_token(token: str) -> int | None:
    """
    Verify a JWT access token and return the user_id.
    Returns None if the token is invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("token_type") != "access":
            logger.warning("[MCP Auth] Rejected non-access token type")
            return None

        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("[MCP Auth] Token missing user_id")
            return None

        return user_id
    except JWTError as e:
        logger.warning(f"[MCP Auth] JWT verification failed: {e}")
        return None


def get_authenticated_user_id() -> int:
    """
    Get the authenticated user_id from the current context.
    Raises ValueError if no authenticated user is present.
    """
    user_id = authenticated_user_id.get()
    if user_id is None:
        raise ValueError("No authenticated user in current context. JWT auth required.")
    return user_id


class JWTAuthMiddleware:
    """
    ASGI middleware that validates JWT Bearer tokens on every HTTP request.
    Uses a raw ASGI implementation (not BaseHTTPMiddleware) to avoid
    buffering SSE streaming responses.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract Authorization header from raw ASGI headers
        headers = dict(scope.get("headers", []))
        auth_value = headers.get(b"authorization", b"").decode()

        if not auth_value.startswith("Bearer "):
            await self._send_401(send, "Missing or invalid Authorization header. Use: Bearer <token>")
            return

        token = auth_value[7:]
        user_id = verify_jwt_token(token)

        if user_id is None:
            await self._send_401(send, "Invalid or expired JWT token")
            return

        logger.info(f"[MCP Auth] Authenticated user_id={user_id}")

        # Set the user_id in context for the duration of this request
        ctx_token = authenticated_user_id.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            authenticated_user_id.reset(ctx_token)

    @staticmethod
    async def _send_401(send, detail: str):
        """Send a 401 Unauthorized JSON response."""
        import json
        body = json.dumps({"error": "Unauthorized", "detail": detail}).encode()
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                [b"content-type", b"application/json"],
                [b"www-authenticate", b"Bearer"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
