"""
MCP Server exposing Goals/Tasks/Words operations as tools.
Uses SSE transport on port 8002.

DELETE tools are intentionally excluded from this MCP server to prevent
the LLM from accidentally deleting user data (goals, tasks, tags, words).
The underlying delete functions still exist in tools_goals.py / tools_words.py
for use by other internal code paths if needed.

When accessed via the MCP Server (external), user_id is extracted from
the JWT token by the auth middleware. The tool functions do NOT accept
user_id as a parameter -- this prevents external clients from spoofing
other users' identities.

The underlying async functions in tools_goals.py / tools_words.py still
accept user_id as a parameter and are used directly by the internal
LangGraph agent (api/agent/tools.py) -- that path is unaffected.
"""
import os
import sys
from pathlib import Path

# Setup Django before anything else
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root_directory.settings')

import django
django.setup()

from mcp.server.fastmcp import FastMCP

from .auth import get_authenticated_user_id
from .tools_goals import (
    list_goals, get_goal, create_goal, update_goal,
    list_tasks, get_task, create_task, update_task,
    list_goal_tags, get_goal_tag, create_goal_tag, update_goal_tag,
)
from .tools_words import (
    list_words, get_word, create_word, update_word,
    list_word_tags, get_word_tag, create_word_tag, update_word_tag,
)
from .tools_email import (
    get_email_config, update_email_config, send_test_email, list_email_history,
)

mcp = FastMCP("Goals MCP Server")


# ==================== Goal Tools ====================

@mcp.tool()
async def tool_list_goals(status: str = "", priority: str = "",
                          tag_id: int = 0, skip: int = 0, limit: int = 20) -> str:
    """List all goals for the authenticated user. Optional filters: status (not_started/in_progress/blocked/resolved), priority (very_high/high/medium/low/very_low), tag_id."""
    user_id = get_authenticated_user_id()
    return await list_goals(
        user_id, status=status or None, priority=priority or None,
        tag_id=tag_id or None, skip=skip, limit=limit
    )


@mcp.tool()
async def tool_get_goal(goal_id: int) -> str:
    """Get details of a specific goal by its ID."""
    user_id = get_authenticated_user_id()
    return await get_goal(user_id, goal_id)


@mcp.tool()
async def tool_create_goal(title: str, description: str = "",
                           notes: str = "", status: str = "not_started",
                           priority: str = "medium", urgency: str = "medium",
                           tag_ids: str = "") -> str:
    """Create a new goal. status: not_started/in_progress/blocked/resolved. priority/urgency: very_high/high/medium/low/very_low. tag_ids: comma-separated goal tag IDs."""
    user_id = get_authenticated_user_id()
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_goal(user_id, title, description, notes, status, priority, urgency, parsed_tags)


@mcp.tool()
async def tool_update_goal(goal_id: int, title: str = "",
                           description: str = "", notes: str = "",
                           status: str = "", priority: str = "",
                           urgency: str = "", tag_ids: str = "") -> str:
    """Update an existing goal. Only provide fields you want to change. tag_ids: comma-separated goal tag IDs (empty string = no change, '0' = clear all tags)."""
    user_id = get_authenticated_user_id()
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_goal(
        user_id, goal_id,
        title=title or None, description=description if description != "" else None,
        notes=notes if notes != "" else None, status=status or None,
        priority=priority or None, urgency=urgency or None, tag_ids=parsed_tags
    )


# ==================== Task Tools ====================

@mcp.tool()
async def tool_list_tasks(status: str = "", priority: str = "",
                          goal_id: int = 0, tag_id: int = 0,
                          skip: int = 0, limit: int = 20) -> str:
    """List all tasks for the authenticated user. Optional filters: status (not_done/ongoing/done), priority (very_high/high/medium/low/very_low), goal_id, tag_id."""
    user_id = get_authenticated_user_id()
    return await list_tasks(
        user_id, status=status or None, priority=priority or None,
        goal_id=goal_id or None, tag_id=tag_id or None, skip=skip, limit=limit
    )


@mcp.tool()
async def tool_get_task(task_id: int) -> str:
    """Get details of a specific task by its ID."""
    user_id = get_authenticated_user_id()
    return await get_task(user_id, task_id)


@mcp.tool()
async def tool_create_task(name: str, description: str = "",
                           goal_id: int = 0, status: str = "not_done",
                           priority: str = "medium", urgency: str = "medium",
                           tag_ids: str = "") -> str:
    """Create a new task, optionally linked to a goal. status: not_done/ongoing/done. priority/urgency: very_high/high/medium/low/very_low. tag_ids: comma-separated goal tag IDs. goal_id: ID of the goal to link to (0 = no goal)."""
    user_id = get_authenticated_user_id()
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_task(user_id, name, description, goal_id or None, status, priority, urgency, parsed_tags)


@mcp.tool()
async def tool_update_task(task_id: int, name: str = "",
                           description: str = "", goal_id: int = -1,
                           status: str = "", priority: str = "",
                           urgency: str = "", tag_ids: str = "") -> str:
    """Update an existing task. Only provide fields to change. goal_id: -1 = no change, 0 = unlink from goal, positive = link to goal. tag_ids: comma-separated IDs."""
    user_id = get_authenticated_user_id()
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_task(
        user_id, task_id,
        name=name or None, description=description if description != "" else None,
        goal_id=goal_id if goal_id != -1 else None, status=status or None,
        priority=priority or None, urgency=urgency or None, tag_ids=parsed_tags
    )


# ==================== Goal Tag Tools ====================

@mcp.tool()
async def tool_list_goal_tags(search: str = "", skip: int = 0, limit: int = 50) -> str:
    """List all goal tags for the authenticated user. Optional: search by name."""
    user_id = get_authenticated_user_id()
    return await list_goal_tags(user_id, search=search or None, skip=skip, limit=limit)


@mcp.tool()
async def tool_get_goal_tag(tag_id: int) -> str:
    """Get details of a specific goal tag by its ID."""
    user_id = get_authenticated_user_id()
    return await get_goal_tag(user_id, tag_id)


@mcp.tool()
async def tool_create_goal_tag(name: str) -> str:
    """Create a new goal tag with the given name."""
    user_id = get_authenticated_user_id()
    return await create_goal_tag(user_id, name)


@mcp.tool()
async def tool_update_goal_tag(tag_id: int, name: str) -> str:
    """Update a goal tag's name."""
    user_id = get_authenticated_user_id()
    return await update_goal_tag(user_id, tag_id, name)


# ==================== Word Tools ====================

@mcp.tool()
async def tool_list_words(search: str = "", tag_id: int = 0,
                          skip: int = 0, limit: int = 20) -> str:
    """List all English words for the authenticated user. Optional: search (searches title, explanation, notes), tag_id."""
    user_id = get_authenticated_user_id()
    return await list_words(user_id, search=search or None, tag_id=tag_id or None, skip=skip, limit=limit)


@mcp.tool()
async def tool_get_word(word_id: int) -> str:
    """Get details of a specific English word by its ID."""
    user_id = get_authenticated_user_id()
    return await get_word(user_id, word_id)


@mcp.tool()
async def tool_create_word(title: str, explanation: str,
                           notes: str = "", tag_ids: str = "") -> str:
    """Create a new English word with title and explanation. tag_ids: comma-separated word tag IDs."""
    user_id = get_authenticated_user_id()
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_word(user_id, title, explanation, notes, parsed_tags)


@mcp.tool()
async def tool_update_word(word_id: int, title: str = "",
                           explanation: str = "", notes: str = "",
                           tag_ids: str = "") -> str:
    """Update an existing English word. Only provide fields to change. tag_ids: comma-separated word tag IDs."""
    user_id = get_authenticated_user_id()
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_word(
        user_id, word_id,
        title=title or None, explanation=explanation if explanation != "" else None,
        notes=notes if notes != "" else None, tag_ids=parsed_tags
    )


# ==================== Word Tag Tools ====================

@mcp.tool()
async def tool_list_word_tags(search: str = "", skip: int = 0, limit: int = 50) -> str:
    """List all word tags for the authenticated user. Optional: search by name."""
    user_id = get_authenticated_user_id()
    return await list_word_tags(user_id, search=search or None, skip=skip, limit=limit)


@mcp.tool()
async def tool_get_word_tag(tag_id: int) -> str:
    """Get details of a specific word tag by its ID."""
    user_id = get_authenticated_user_id()
    return await get_word_tag(user_id, tag_id)


@mcp.tool()
async def tool_create_word_tag(name: str) -> str:
    """Create a new word tag with the given name."""
    user_id = get_authenticated_user_id()
    return await create_word_tag(user_id, name)


@mcp.tool()
async def tool_update_word_tag(tag_id: int, name: str) -> str:
    """Update a word tag's name."""
    user_id = get_authenticated_user_id()
    return await update_word_tag(user_id, tag_id, name)


# ==================== Email Tools ====================

@mcp.tool()
async def tool_get_email_config() -> str:
    """Get the authenticated user's email schedule configuration (send times, timezone, recipients, etc.)."""
    user_id = get_authenticated_user_id()
    return await get_email_config(user_id)


@mcp.tool()
async def tool_update_email_config(
    is_active: bool = None,
    timezone: str = "",
    send_times: str = "",
    words_per_email: int = 0,
    extra_recipients: str = "",
    story_language: str = "",
    exclude_word_ids: str = "",
) -> str:
    """Update email schedule config. send_times: comma-separated HH:MM (e.g. '08:00,18:00'). extra_recipients: comma-separated emails (max 3). story_language: 'english' or 'bilingual'. exclude_word_ids: comma-separated IDs."""
    user_id = get_authenticated_user_id()
    return await update_email_config(
        user_id,
        is_active=is_active,
        timezone=timezone or None,
        send_times=send_times or None,
        words_per_email=words_per_email or None,
        extra_recipients=extra_recipients or None,
        story_language=story_language or None,
        exclude_word_ids=exclude_word_ids or None,
    )


@mcp.tool()
async def tool_send_test_email() -> str:
    """Trigger an immediate test story email to the authenticated user (and any extra recipients)."""
    user_id = get_authenticated_user_id()
    return await send_test_email(user_id)


@mcp.tool()
async def tool_list_email_history(skip: int = 0, limit: int = 10) -> str:
    """List recently sent story emails for the authenticated user."""
    user_id = get_authenticated_user_id()
    return await list_email_history(user_id, skip=skip, limit=limit)
