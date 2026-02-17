#!/usr/bin/env python
"""
Entry point to start the MCP Server with SSE transport on port 8002.

JWT Authentication is enforced: external clients must provide a valid
Bearer token in the Authorization header. The user_id is extracted from
the token and used for all tool operations.

Usage:
    python -m api.mcp_server.run_server

    # With custom host/port (e.g., expose to network):
    MCP_HOST=0.0.0.0 MCP_PORT=8002 python -m api.mcp_server.run_server
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root_directory.settings')

# Set MCP server port before importing
os.environ["MCP_SSE_PORT"] = os.environ.get("MCP_PORT", "8002")

import django
django.setup()

import uvicorn
from api.mcp_server.server import mcp
from api.mcp_server.auth import JWTAuthMiddleware

if __name__ == "__main__":
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MCP_PORT", "8002"))

    sse_app = mcp.sse_app()

    # Wrap the SSE app with JWT authentication middleware
    authenticated_app = JWTAuthMiddleware(sse_app)

    print(f"Starting MCP Server on {host}:{port} (JWT auth enabled)")
    print(f"  - Clients must provide: Authorization: Bearer <jwt_token>")
    if host == "127.0.0.1":
        print(f"  - Listening on localhost only (set MCP_HOST=0.0.0.0 to expose)")

    uvicorn.run(authenticated_app, host=host, port=port)
