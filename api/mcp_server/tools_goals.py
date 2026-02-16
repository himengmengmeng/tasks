"""MCP tools for Goals, Tasks, and Goal Tags CRUD operations."""
import json
from asgiref.sync import sync_to_async


def _serialize_goal(goal, tag_names):
    """Serialize a Goal object to dict."""
    return {
        "id": goal.id,
        "title": goal.title,
        "description": goal.description or "",
        "notes": goal.notes or "",
        "status": goal.status,
        "priority": goal.priority,
        "urgency": goal.urgency,
        "created_time": goal.created_time.isoformat(),
        "tags": tag_names,
    }


def _serialize_task(task, tag_names):
    """Serialize a Task object to dict."""
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description or "",
        "goal_id": task.goal_id,
        "goal_title": task.goal.title if task.goal else None,
        "status": task.status,
        "priority": task.priority,
        "urgency": task.urgency,
        "created_time": task.created_time.isoformat(),
        "tags": tag_names,
    }


def _serialize_goal_tag(tag, goal_count=0, task_count=0):
    """Serialize a Goal Tag object to dict."""
    return {
        "id": tag.id,
        "name": tag.name,
        "created_at": tag.created_at.isoformat(),
        "goal_count": goal_count,
        "task_count": task_count,
    }


# ==================== Goal Tools ====================

async def list_goals(user_id: int, status: str = None, priority: str = None, tag_id: int = None, skip: int = 0, limit: int = 20) -> str:
    """List goals for the user with optional filters."""
    from goal_app.models import Goal
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    queryset = Goal.objects.filter(creator=user).select_related('creator').prefetch_related('tags')

    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if tag_id:
        queryset = queryset.filter(tags__id=tag_id)

    total = await sync_to_async(queryset.count)()
    goals = await sync_to_async(list)(queryset.order_by('-created_time')[skip:skip + limit])

    results = []
    for goal in goals:
        tag_names = await sync_to_async(list)(goal.tags.values_list('name', flat=True))
        results.append(_serialize_goal(goal, tag_names))

    return json.dumps({"goals": results, "total": total}, ensure_ascii=False)


async def get_goal(user_id: int, goal_id: int) -> str:
    """Get a specific goal by ID."""
    from goal_app.models import Goal
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        goal = await sync_to_async(
            Goal.objects.select_related('creator').prefetch_related('tags').get
        )(id=goal_id, creator=user)
        tag_names = await sync_to_async(list)(goal.tags.values_list('name', flat=True))
        return json.dumps(_serialize_goal(goal, tag_names), ensure_ascii=False)
    except Goal.DoesNotExist:
        return json.dumps({"error": f"Goal with id {goal_id} not found"})


async def create_goal(user_id: int, title: str, description: str = "", notes: str = "",
                      status: str = "not_started", priority: str = "medium",
                      urgency: str = "medium", tag_ids: list = None) -> str:
    """Create a new goal."""
    from goal_app.models import Goal, Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    goal = await sync_to_async(Goal.objects.create)(
        title=title,
        description=description or None,
        notes=notes or None,
        status=status,
        priority=priority,
        urgency=urgency,
        creator=user
    )

    if tag_ids:
        tags = await sync_to_async(list)(GoalTag.objects.filter(id__in=tag_ids, creator=user))
        await sync_to_async(goal.tags.set)(tags)

    goal = await sync_to_async(
        Goal.objects.select_related('creator').prefetch_related('tags').get
    )(id=goal.id)
    tag_names = await sync_to_async(list)(goal.tags.values_list('name', flat=True))
    return json.dumps({"message": "Goal created successfully", "goal": _serialize_goal(goal, tag_names)}, ensure_ascii=False)


async def update_goal(user_id: int, goal_id: int, title: str = None, description: str = None,
                      notes: str = None, status: str = None, priority: str = None,
                      urgency: str = None, tag_ids: list = None) -> str:
    """Update an existing goal."""
    from goal_app.models import Goal, Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        goal = await sync_to_async(
            Goal.objects.select_related('creator').prefetch_related('tags').get
        )(id=goal_id, creator=user)
    except Goal.DoesNotExist:
        return json.dumps({"error": f"Goal with id {goal_id} not found"})

    if title is not None:
        goal.title = title
    if description is not None:
        goal.description = description
    if notes is not None:
        goal.notes = notes
    if status is not None:
        goal.status = status
    if priority is not None:
        goal.priority = priority
    if urgency is not None:
        goal.urgency = urgency

    await sync_to_async(goal.save)()

    if tag_ids is not None:
        tags = await sync_to_async(list)(GoalTag.objects.filter(id__in=tag_ids, creator=user))
        await sync_to_async(goal.tags.set)(tags)

    goal = await sync_to_async(
        Goal.objects.select_related('creator').prefetch_related('tags').get
    )(id=goal.id)
    tag_names = await sync_to_async(list)(goal.tags.values_list('name', flat=True))
    return json.dumps({"message": "Goal updated successfully", "goal": _serialize_goal(goal, tag_names)}, ensure_ascii=False)


async def delete_goal(user_id: int, goal_id: int) -> str:
    """Delete a goal by ID."""
    from goal_app.models import Goal
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        goal = await sync_to_async(Goal.objects.get)(id=goal_id, creator=user)
        goal_title = goal.title
        await sync_to_async(goal.delete)()
        return json.dumps({"message": f"Goal '{goal_title}' deleted successfully"})
    except Goal.DoesNotExist:
        return json.dumps({"error": f"Goal with id {goal_id} not found"})


# ==================== Task Tools ====================

async def list_tasks(user_id: int, status: str = None, priority: str = None,
                     goal_id: int = None, tag_id: int = None,
                     skip: int = 0, limit: int = 20) -> str:
    """List tasks for the user with optional filters."""
    from goal_app.models import Task
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    queryset = Task.objects.filter(creator=user).select_related('goal').prefetch_related('tags')

    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if goal_id:
        queryset = queryset.filter(goal_id=goal_id)
    if tag_id:
        queryset = queryset.filter(tags__id=tag_id)

    total = await sync_to_async(queryset.count)()
    tasks = await sync_to_async(list)(queryset.order_by('-created_time')[skip:skip + limit])

    results = []
    for task in tasks:
        tag_names = await sync_to_async(list)(task.tags.values_list('name', flat=True))
        results.append(_serialize_task(task, tag_names))

    return json.dumps({"tasks": results, "total": total}, ensure_ascii=False)


async def get_task(user_id: int, task_id: int) -> str:
    """Get a specific task by ID."""
    from goal_app.models import Task
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        task = await sync_to_async(
            Task.objects.select_related('goal').prefetch_related('tags').get
        )(id=task_id, creator=user)
        tag_names = await sync_to_async(list)(task.tags.values_list('name', flat=True))
        return json.dumps(_serialize_task(task, tag_names), ensure_ascii=False)
    except Task.DoesNotExist:
        return json.dumps({"error": f"Task with id {task_id} not found"})


async def create_task(user_id: int, name: str, description: str = "", goal_id: int = None,
                      status: str = "not_done", priority: str = "medium",
                      urgency: str = "medium", tag_ids: list = None) -> str:
    """Create a new task, optionally linked to a goal."""
    from goal_app.models import Task, Goal, Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    goal = None
    if goal_id:
        try:
            goal = await sync_to_async(Goal.objects.get)(id=goal_id, creator=user)
        except Goal.DoesNotExist:
            return json.dumps({"error": f"Goal with id {goal_id} not found"})

    task = await sync_to_async(Task.objects.create)(
        name=name,
        description=description or None,
        goal=goal,
        status=status,
        priority=priority,
        urgency=urgency,
        creator=user
    )

    if tag_ids:
        tags = await sync_to_async(list)(GoalTag.objects.filter(id__in=tag_ids, creator=user))
        await sync_to_async(task.tags.set)(tags)

    task = await sync_to_async(
        Task.objects.select_related('goal').prefetch_related('tags').get
    )(id=task.id)
    tag_names = await sync_to_async(list)(task.tags.values_list('name', flat=True))
    return json.dumps({"message": "Task created successfully", "task": _serialize_task(task, tag_names)}, ensure_ascii=False)


async def update_task(user_id: int, task_id: int, name: str = None, description: str = None,
                      goal_id: int = None, status: str = None, priority: str = None,
                      urgency: str = None, tag_ids: list = None) -> str:
    """Update an existing task."""
    from goal_app.models import Task, Goal, Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        task = await sync_to_async(
            Task.objects.select_related('goal').prefetch_related('tags').get
        )(id=task_id, creator=user)
    except Task.DoesNotExist:
        return json.dumps({"error": f"Task with id {task_id} not found"})

    if name is not None:
        task.name = name
    if description is not None:
        task.description = description
    if status is not None:
        task.status = status
    if priority is not None:
        task.priority = priority
    if urgency is not None:
        task.urgency = urgency
    if goal_id is not None:
        if goal_id == 0:
            task.goal = None
        else:
            try:
                goal = await sync_to_async(Goal.objects.get)(id=goal_id, creator=user)
                task.goal = goal
            except Goal.DoesNotExist:
                return json.dumps({"error": f"Goal with id {goal_id} not found"})

    await sync_to_async(task.save)()

    if tag_ids is not None:
        tags = await sync_to_async(list)(GoalTag.objects.filter(id__in=tag_ids, creator=user))
        await sync_to_async(task.tags.set)(tags)

    task = await sync_to_async(
        Task.objects.select_related('goal').prefetch_related('tags').get
    )(id=task.id)
    tag_names = await sync_to_async(list)(task.tags.values_list('name', flat=True))
    return json.dumps({"message": "Task updated successfully", "task": _serialize_task(task, tag_names)}, ensure_ascii=False)


async def delete_task(user_id: int, task_id: int) -> str:
    """Delete a task by ID."""
    from goal_app.models import Task
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        task = await sync_to_async(Task.objects.get)(id=task_id, creator=user)
        task_name = task.name
        await sync_to_async(task.delete)()
        return json.dumps({"message": f"Task '{task_name}' deleted successfully"})
    except Task.DoesNotExist:
        return json.dumps({"error": f"Task with id {task_id} not found"})


# ==================== Goal Tag Tools ====================

async def list_goal_tags(user_id: int, search: str = None, skip: int = 0, limit: int = 50) -> str:
    """List goal tags for the user."""
    from goal_app.models import Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    queryset = GoalTag.objects.filter(creator=user)

    if search:
        queryset = queryset.filter(name__icontains=search)

    total = await sync_to_async(queryset.count)()
    tags = await sync_to_async(list)(queryset.order_by('-created_at')[skip:skip + limit])

    results = []
    for tag in tags:
        goal_count = await sync_to_async(tag.goals.count)()
        task_count = await sync_to_async(tag.tasks.count)()
        results.append(_serialize_goal_tag(tag, goal_count, task_count))

    return json.dumps({"tags": results, "total": total}, ensure_ascii=False)


async def get_goal_tag(user_id: int, tag_id: int) -> str:
    """Get a specific goal tag by ID."""
    from goal_app.models import Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        tag = await sync_to_async(GoalTag.objects.get)(id=tag_id, creator=user)
        goal_count = await sync_to_async(tag.goals.count)()
        task_count = await sync_to_async(tag.tasks.count)()
        return json.dumps(_serialize_goal_tag(tag, goal_count, task_count), ensure_ascii=False)
    except GoalTag.DoesNotExist:
        return json.dumps({"error": f"Goal tag with id {tag_id} not found"})


async def create_goal_tag(user_id: int, name: str) -> str:
    """Create a new goal tag."""
    from goal_app.models import Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    exists = await sync_to_async(GoalTag.objects.filter(name=name, creator=user).exists)()
    if exists:
        return json.dumps({"error": f"Goal tag '{name}' already exists"})

    tag = await sync_to_async(GoalTag.objects.create)(name=name, creator=user)
    return json.dumps({"message": f"Goal tag '{name}' created successfully", "tag": _serialize_goal_tag(tag)}, ensure_ascii=False)


async def update_goal_tag(user_id: int, tag_id: int, name: str) -> str:
    """Update a goal tag's name."""
    from goal_app.models import Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        tag = await sync_to_async(GoalTag.objects.get)(id=tag_id, creator=user)
    except GoalTag.DoesNotExist:
        return json.dumps({"error": f"Goal tag with id {tag_id} not found"})

    if name != tag.name:
        exists = await sync_to_async(GoalTag.objects.filter(name=name, creator=user).exclude(id=tag_id).exists)()
        if exists:
            return json.dumps({"error": f"Goal tag '{name}' already exists"})

    tag.name = name
    await sync_to_async(tag.save)()
    goal_count = await sync_to_async(tag.goals.count)()
    task_count = await sync_to_async(tag.tasks.count)()
    return json.dumps({"message": f"Goal tag updated to '{name}'", "tag": _serialize_goal_tag(tag, goal_count, task_count)}, ensure_ascii=False)


async def delete_goal_tag(user_id: int, tag_id: int) -> str:
    """Delete a goal tag by ID."""
    from goal_app.models import Tag as GoalTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        tag = await sync_to_async(GoalTag.objects.get)(id=tag_id, creator=user)
        tag_name = tag.name
        await sync_to_async(tag.delete)()
        return json.dumps({"message": f"Goal tag '{tag_name}' deleted successfully"})
    except GoalTag.DoesNotExist:
        return json.dumps({"error": f"Goal tag with id {tag_id} not found"})
