"""
MCP Server exposing Goals/Tasks/Words CRUD operations as tools.
Uses SSE transport on port 8002.
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

from .tools_goals import (
    list_goals, get_goal, create_goal, update_goal, delete_goal,
    list_tasks, get_task, create_task, update_task, delete_task,
    list_goal_tags, get_goal_tag, create_goal_tag, update_goal_tag, delete_goal_tag,
)
from .tools_words import (
    list_words, get_word, create_word, update_word, delete_word,
    list_word_tags, get_word_tag, create_word_tag, update_word_tag, delete_word_tag,
)

mcp = FastMCP("Goals MCP Server")


# ==================== Goal Tools ====================

@mcp.tool()
async def tool_list_goals(user_id: int, status: str = "", priority: str = "",
                          tag_id: int = 0, skip: int = 0, limit: int = 20) -> str:
    """List all goals for the user. Optional filters: status (not_started/in_progress/blocked/resolved), priority (very_high/high/medium/low/very_low), tag_id."""
    return await list_goals(
        user_id, status=status or None, priority=priority or None,
        tag_id=tag_id or None, skip=skip, limit=limit
    )


@mcp.tool()
async def tool_get_goal(user_id: int, goal_id: int) -> str:
    """Get details of a specific goal by its ID."""
    return await get_goal(user_id, goal_id)


@mcp.tool()
async def tool_create_goal(user_id: int, title: str, description: str = "",
                           notes: str = "", status: str = "not_started",
                           priority: str = "medium", urgency: str = "medium",
                           tag_ids: str = "") -> str:
    """Create a new goal. status: not_started/in_progress/blocked/resolved. priority/urgency: very_high/high/medium/low/very_low. tag_ids: comma-separated goal tag IDs."""
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_goal(user_id, title, description, notes, status, priority, urgency, parsed_tags)


@mcp.tool()
async def tool_update_goal(user_id: int, goal_id: int, title: str = "",
                           description: str = "", notes: str = "",
                           status: str = "", priority: str = "",
                           urgency: str = "", tag_ids: str = "") -> str:
    """Update an existing goal. Only provide fields you want to change. tag_ids: comma-separated goal tag IDs (empty string = no change, '0' = clear all tags)."""
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_goal(
        user_id, goal_id,
        title=title or None, description=description if description != "" else None,
        notes=notes if notes != "" else None, status=status or None,
        priority=priority or None, urgency=urgency or None, tag_ids=parsed_tags
    )


@mcp.tool()
async def tool_delete_goal(user_id: int, goal_id: int) -> str:
    """Delete a goal by its ID. This action cannot be undone."""
    return await delete_goal(user_id, goal_id)


# ==================== Task Tools ====================

@mcp.tool()
async def tool_list_tasks(user_id: int, status: str = "", priority: str = "",
                          goal_id: int = 0, tag_id: int = 0,
                          skip: int = 0, limit: int = 20) -> str:
    """List all tasks for the user. Optional filters: status (not_done/ongoing/done), priority (very_high/high/medium/low/very_low), goal_id, tag_id."""
    return await list_tasks(
        user_id, status=status or None, priority=priority or None,
        goal_id=goal_id or None, tag_id=tag_id or None, skip=skip, limit=limit
    )


@mcp.tool()
async def tool_get_task(user_id: int, task_id: int) -> str:
    """Get details of a specific task by its ID."""
    return await get_task(user_id, task_id)


@mcp.tool()
async def tool_create_task(user_id: int, name: str, description: str = "",
                           goal_id: int = 0, status: str = "not_done",
                           priority: str = "medium", urgency: str = "medium",
                           tag_ids: str = "") -> str:
    """Create a new task, optionally linked to a goal. status: not_done/ongoing/done. priority/urgency: very_high/high/medium/low/very_low. tag_ids: comma-separated goal tag IDs. goal_id: ID of the goal to link to (0 = no goal)."""
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_task(user_id, name, description, goal_id or None, status, priority, urgency, parsed_tags)


@mcp.tool()
async def tool_update_task(user_id: int, task_id: int, name: str = "",
                           description: str = "", goal_id: int = -1,
                           status: str = "", priority: str = "",
                           urgency: str = "", tag_ids: str = "") -> str:
    """Update an existing task. Only provide fields to change. goal_id: -1 = no change, 0 = unlink from goal, positive = link to goal. tag_ids: comma-separated IDs."""
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_task(
        user_id, task_id,
        name=name or None, description=description if description != "" else None,
        goal_id=goal_id if goal_id != -1 else None, status=status or None,
        priority=priority or None, urgency=urgency or None, tag_ids=parsed_tags
    )


@mcp.tool()
async def tool_delete_task(user_id: int, task_id: int) -> str:
    """Delete a task by its ID. This action cannot be undone."""
    return await delete_task(user_id, task_id)


# ==================== Goal Tag Tools ====================

@mcp.tool()
async def tool_list_goal_tags(user_id: int, search: str = "", skip: int = 0, limit: int = 50) -> str:
    """List all goal tags for the user. Optional: search by name."""
    return await list_goal_tags(user_id, search=search or None, skip=skip, limit=limit)


@mcp.tool()
async def tool_get_goal_tag(user_id: int, tag_id: int) -> str:
    """Get details of a specific goal tag by its ID."""
    return await get_goal_tag(user_id, tag_id)


@mcp.tool()
async def tool_create_goal_tag(user_id: int, name: str) -> str:
    """Create a new goal tag with the given name."""
    return await create_goal_tag(user_id, name)


@mcp.tool()
async def tool_update_goal_tag(user_id: int, tag_id: int, name: str) -> str:
    """Update a goal tag's name."""
    return await update_goal_tag(user_id, tag_id, name)


@mcp.tool()
async def tool_delete_goal_tag(user_id: int, tag_id: int) -> str:
    """Delete a goal tag by its ID."""
    return await delete_goal_tag(user_id, tag_id)


# ==================== Word Tools ====================

@mcp.tool()
async def tool_list_words(user_id: int, search: str = "", tag_id: int = 0,
                          skip: int = 0, limit: int = 20) -> str:
    """List all English words for the user. Optional: search (searches title, explanation, notes), tag_id."""
    return await list_words(user_id, search=search or None, tag_id=tag_id or None, skip=skip, limit=limit)


@mcp.tool()
async def tool_get_word(user_id: int, word_id: int) -> str:
    """Get details of a specific English word by its ID."""
    return await get_word(user_id, word_id)


@mcp.tool()
async def tool_create_word(user_id: int, title: str, explanation: str,
                           notes: str = "", tag_ids: str = "") -> str:
    """Create a new English word with title and explanation. tag_ids: comma-separated word tag IDs."""
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_word(user_id, title, explanation, notes, parsed_tags)


@mcp.tool()
async def tool_update_word(user_id: int, word_id: int, title: str = "",
                           explanation: str = "", notes: str = "",
                           tag_ids: str = "") -> str:
    """Update an existing English word. Only provide fields to change. tag_ids: comma-separated word tag IDs."""
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_word(
        user_id, word_id,
        title=title or None, explanation=explanation if explanation != "" else None,
        notes=notes if notes != "" else None, tag_ids=parsed_tags
    )


@mcp.tool()
async def tool_delete_word(user_id: int, word_id: int) -> str:
    """Delete an English word by its ID. This action cannot be undone."""
    return await delete_word(user_id, word_id)


# ==================== Word Tag Tools ====================

@mcp.tool()
async def tool_list_word_tags(user_id: int, search: str = "", skip: int = 0, limit: int = 50) -> str:
    """List all word tags for the user. Optional: search by name."""
    return await list_word_tags(user_id, search=search or None, skip=skip, limit=limit)


@mcp.tool()
async def tool_get_word_tag(user_id: int, tag_id: int) -> str:
    """Get details of a specific word tag by its ID."""
    return await get_word_tag(user_id, tag_id)


@mcp.tool()
async def tool_create_word_tag(user_id: int, name: str) -> str:
    """Create a new word tag with the given name."""
    return await create_word_tag(user_id, name)


@mcp.tool()
async def tool_update_word_tag(user_id: int, tag_id: int, name: str) -> str:
    """Update a word tag's name."""
    return await update_word_tag(user_id, tag_id, name)


@mcp.tool()
async def tool_delete_word_tag(user_id: int, tag_id: int) -> str:
    """Delete a word tag by its ID."""
    return await delete_word_tag(user_id, tag_id)
