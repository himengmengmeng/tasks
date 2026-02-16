#!/usr/bin/env python
"""Entry point to start the MCP Server with SSE transport on port 8002."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root_directory.settings')

# Set MCP server port before importing
os.environ["MCP_SSE_PORT"] = "8002"

import django
django.setup()

import uvicorn
from api.mcp_server.server import mcp

if __name__ == "__main__":
    sse_app = mcp.sse_app()
    uvicorn.run(sse_app, host="0.0.0.0", port=8002)
