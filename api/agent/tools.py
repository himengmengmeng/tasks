"""
LangChain-compatible tool wrappers that call the MCP server tools directly.
Instead of going through MCP transport, we call the underlying async functions
directly for simplicity and performance within the same process.
"""
from langchain_core.tools import tool

from api.mcp_server.tools_goals import (
    list_goals, get_goal, create_goal, update_goal, delete_goal,
    list_tasks, get_task, create_task, update_task, delete_task,
    list_goal_tags, get_goal_tag, create_goal_tag, update_goal_tag, delete_goal_tag,
)
from api.mcp_server.tools_words import (
    list_words, get_word, create_word, update_word, delete_word,
    list_word_tags, get_word_tag, create_word_tag, update_word_tag, delete_word_tag,
)
from api.mcp_server.tools_email import (
    get_email_config, update_email_config, send_test_email, list_email_history,
)


# ==================== Goal Tools ====================

@tool
async def tool_list_goals(user_id: int, status: str = "", priority: str = "",
                          tag_id: int = 0, skip: int = 0, limit: int = 20) -> str:
    """List all goals for the user. Optional filters: status (not_started/in_progress/blocked/resolved), priority (very_high/high/medium/low/very_low), tag_id."""
    return await list_goals(
        user_id, status=status or None, priority=priority or None,
        tag_id=tag_id or None, skip=skip, limit=limit
    )


@tool
async def tool_get_goal(user_id: int, goal_id: int) -> str:
    """Get details of a specific goal by its ID."""
    return await get_goal(user_id, goal_id)


@tool
async def tool_create_goal(user_id: int, title: str, description: str = "",
                           notes: str = "", status: str = "not_started",
                           priority: str = "medium", urgency: str = "medium",
                           tag_ids: str = "") -> str:
    """Create a new goal. status: not_started/in_progress/blocked/resolved. priority/urgency: very_high/high/medium/low/very_low. tag_ids: comma-separated goal tag IDs."""
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_goal(user_id, title, description, notes, status, priority, urgency, parsed_tags)


@tool
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


@tool
async def tool_delete_goal(user_id: int, goal_id: int) -> str:
    """Delete a goal by its ID. This action cannot be undone."""
    return await delete_goal(user_id, goal_id)


# ==================== Task Tools ====================

@tool
async def tool_list_tasks(user_id: int, status: str = "", priority: str = "",
                          goal_id: int = 0, tag_id: int = 0,
                          skip: int = 0, limit: int = 20) -> str:
    """List all tasks for the user. Optional filters: status (not_done/ongoing/done), priority, goal_id, tag_id."""
    return await list_tasks(
        user_id, status=status or None, priority=priority or None,
        goal_id=goal_id or None, tag_id=tag_id or None, skip=skip, limit=limit
    )


@tool
async def tool_get_task(user_id: int, task_id: int) -> str:
    """Get details of a specific task by its ID."""
    return await get_task(user_id, task_id)


@tool
async def tool_create_task(user_id: int, name: str, description: str = "",
                           goal_id: int = 0, status: str = "not_done",
                           priority: str = "medium", urgency: str = "medium",
                           tag_ids: str = "") -> str:
    """Create a new task, optionally linked to a goal. status: not_done/ongoing/done. goal_id: 0 means no goal. tag_ids: comma-separated goal tag IDs."""
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_task(user_id, name, description, goal_id or None, status, priority, urgency, parsed_tags)


@tool
async def tool_update_task(user_id: int, task_id: int, name: str = "",
                           description: str = "", goal_id: int = -1,
                           status: str = "", priority: str = "",
                           urgency: str = "", tag_ids: str = "") -> str:
    """Update an existing task. Only provide fields to change. goal_id: -1 = no change, 0 = unlink, positive = link to goal. tag_ids: comma-separated IDs."""
    parsed_tags = None
    if tag_ids != "":
        parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids != "0" else []
    return await update_task(
        user_id, task_id,
        name=name or None, description=description if description != "" else None,
        goal_id=goal_id if goal_id != -1 else None, status=status or None,
        priority=priority or None, urgency=urgency or None, tag_ids=parsed_tags
    )


@tool
async def tool_delete_task(user_id: int, task_id: int) -> str:
    """Delete a task by its ID. This action cannot be undone."""
    return await delete_task(user_id, task_id)


# ==================== Goal Tag Tools ====================

@tool
async def tool_list_goal_tags(user_id: int, search: str = "", skip: int = 0, limit: int = 50) -> str:
    """List all goal tags for the user. Optional: search by name."""
    return await list_goal_tags(user_id, search=search or None, skip=skip, limit=limit)


@tool
async def tool_get_goal_tag(user_id: int, tag_id: int) -> str:
    """Get details of a specific goal tag by its ID."""
    return await get_goal_tag(user_id, tag_id)


@tool
async def tool_create_goal_tag(user_id: int, name: str) -> str:
    """Create a new goal tag with the given name."""
    return await create_goal_tag(user_id, name)


@tool
async def tool_update_goal_tag(user_id: int, tag_id: int, name: str) -> str:
    """Update a goal tag's name."""
    return await update_goal_tag(user_id, tag_id, name)


@tool
async def tool_delete_goal_tag(user_id: int, tag_id: int) -> str:
    """Delete a goal tag by its ID."""
    return await delete_goal_tag(user_id, tag_id)


# ==================== Word Tools ====================

@tool
async def tool_list_words(user_id: int, search: str = "", tag_id: int = 0,
                          skip: int = 0, limit: int = 20) -> str:
    """List all English words for the user. Optional: search (searches title, explanation, notes), tag_id."""
    return await list_words(user_id, search=search or None, tag_id=tag_id or None, skip=skip, limit=limit)


@tool
async def tool_get_word(user_id: int, word_id: int) -> str:
    """Get details of a specific English word by its ID."""
    return await get_word(user_id, word_id)


@tool
async def tool_create_word(user_id: int, title: str, explanation: str,
                           notes: str = "", tag_ids: str = "") -> str:
    """Create a new English word. Requires title and explanation. tag_ids: comma-separated word tag IDs."""
    parsed_tags = [int(x.strip()) for x in tag_ids.split(",") if x.strip()] if tag_ids else None
    return await create_word(user_id, title, explanation, notes, parsed_tags)


@tool
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


@tool
async def tool_delete_word(user_id: int, word_id: int) -> str:
    """Delete an English word by its ID. This action cannot be undone."""
    return await delete_word(user_id, word_id)


# ==================== Word Tag Tools ====================

@tool
async def tool_list_word_tags(user_id: int, search: str = "", skip: int = 0, limit: int = 50) -> str:
    """List all word tags for the user. Optional: search by name."""
    return await list_word_tags(user_id, search=search or None, skip=skip, limit=limit)


@tool
async def tool_get_word_tag(user_id: int, tag_id: int) -> str:
    """Get details of a specific word tag by its ID."""
    return await get_word_tag(user_id, tag_id)


@tool
async def tool_create_word_tag(user_id: int, name: str) -> str:
    """Create a new word tag with the given name."""
    return await create_word_tag(user_id, name)


@tool
async def tool_update_word_tag(user_id: int, tag_id: int, name: str) -> str:
    """Update a word tag's name."""
    return await update_word_tag(user_id, tag_id, name)


@tool
async def tool_delete_word_tag(user_id: int, tag_id: int) -> str:
    """Delete a word tag by its ID."""
    return await delete_word_tag(user_id, tag_id)


# ==================== Email Tools ====================

@tool
async def tool_get_email_config(user_id: int) -> str:
    """Get the user's email schedule configuration (send times, timezone, recipients, language, etc.)."""
    return await get_email_config(user_id)


@tool
async def tool_update_email_config(
    user_id: int,
    is_active: bool = None,
    timezone: str = "",
    send_times: str = "",
    words_per_email: int = 0,
    extra_recipients: str = "",
    story_language: str = "",
    exclude_word_ids: str = "",
) -> str:
    """Update the user's email schedule config. send_times: comma-separated HH:MM (e.g. '08:00,18:00'). extra_recipients: comma-separated emails (max 3). story_language: 'english' or 'bilingual'. exclude_word_ids: comma-separated IDs to exclude."""
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


@tool
async def tool_send_test_email(user_id: int) -> str:
    """Trigger an immediate test story email for the user (sends to user email + extra recipients)."""
    return await send_test_email(user_id)


@tool
async def tool_list_email_history(user_id: int, skip: int = 0, limit: int = 10) -> str:
    """List recently sent story emails for the user."""
    return await list_email_history(user_id, skip=skip, limit=limit)


def get_all_tools():
    """Return all available tools."""
    return [
        tool_list_goals, tool_get_goal, tool_create_goal, tool_update_goal, tool_delete_goal,
        tool_list_tasks, tool_get_task, tool_create_task, tool_update_task, tool_delete_task,
        tool_list_goal_tags, tool_get_goal_tag, tool_create_goal_tag, tool_update_goal_tag, tool_delete_goal_tag,
        tool_list_words, tool_get_word, tool_create_word, tool_update_word, tool_delete_word,
        tool_list_word_tags, tool_get_word_tag, tool_create_word_tag, tool_update_word_tag, tool_delete_word_tag,
        tool_get_email_config, tool_update_email_config, tool_send_test_email, tool_list_email_history,
    ]
