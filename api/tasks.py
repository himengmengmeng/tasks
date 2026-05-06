# === tasks.py - 修复更新函数的异步问题 ===
from typing import TYPE_CHECKING, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
from .auth import get_current_active_user

# 🎯 类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()

router = APIRouter()

# Pydantic 模型
class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    goal_id: Optional[int] = None
    status: str = "not_done"
    priority: str = "medium"
    urgency: str = "medium"

class TaskCreate(TaskBase):
    tags: Optional[List[int]] = []

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    goal_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    urgency: Optional[str] = None
    tags: Optional[List[int]] = None

class TaskResponse(TaskBase):
    id: int
    creator_id: int
    created_time: datetime
    tags: List[str] = []
    goal_title: Optional[str] = None
    
    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    size: int

# 异步查询函数
async def async_get_tasks(queryset, skip: int, limit: int):
    """异步执行任务查询"""
    total = await sync_to_async(queryset.count)()
    tasks = await sync_to_async(list)(queryset.order_by('-created_time')[skip:skip + limit])
    return tasks, total

async def async_task_to_response(task) -> TaskResponse:
    """异步将 Django Task 模型转换为 Pydantic 响应模型"""
    # 异步获取标签
    tags_queryset = task.tags.all()
    tag_names = await sync_to_async(list)(tags_queryset.values_list('name', flat=True))
    
    # 获取目标标题
    goal_title = None
    if task.goal:
        goal_title = task.goal.title
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        goal_id=task.goal_id,
        status=task.status,
        priority=task.priority,
        urgency=task.urgency,
        creator_id=task.creator_id,
        created_time=task.created_time,
        tags=tag_names,
        goal_title=goal_title
    )

# 修复：创建同步函数来获取目标
def sync_get_goal(goal_id, creator):
    """同步函数：获取目标"""
    from goal_app.models import Goal
    return Goal.objects.filter(id=goal_id, creator=creator).first()

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    status: Optional[List[str]] = Query(None, description="按状态过滤(可多选)"),
    priority: Optional[List[str]] = Query(None, description="按优先级过滤(可多选)"),
    goal_id: Optional[List[int]] = Query(None, description="按目标ID过滤(可多选)"),
    tag_id: Optional[List[int]] = Query(None, description="按标签ID过滤(可多选)"),
    current_user: User = Depends(get_current_active_user)
) -> TaskListResponse:
    """获取任务列表"""
    try:
        from goal_app.models import Task
        
        # 构建查询
        queryset = Task.objects.filter(creator=current_user)
        
        # 应用过滤器（支持多选）
        # Task 模型里「进行中」存的是 ongoing；历史上前端曾用 in_progress。
        # 多选时若只传 in_progress，会漏掉库里为 ongoing 的记录，这里合并两者。
        if status:
            expanded_status: List[str] = list(status)
            for s in status:
                if s == "in_progress":
                    expanded_status.append("ongoing")
                elif s == "ongoing":
                    expanded_status.append("in_progress")
            queryset = queryset.filter(status__in=expanded_status)
        if priority:
            queryset = queryset.filter(priority__in=priority)
        if goal_id:
            queryset = queryset.filter(goal_id__in=goal_id)
        if tag_id:
            queryset = queryset.filter(tags__id__in=tag_id).distinct()
        
        # 预取相关对象
        queryset = queryset.select_related('goal').prefetch_related('tags')
        
        # 使用异步方式获取数据
        tasks, total = await async_get_tasks(queryset, skip, limit)
        
        # 异步转换为响应模型
        task_responses = []
        for task in tasks:
            response = await async_task_to_response(task)
            task_responses.append(response)
        
        return TaskListResponse(
            tasks=task_responses,
            total=total,
            page=skip // limit + 1,
            size=len(task_responses)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user)
) -> TaskResponse:
    """获取单个任务详情"""
    try:
        from goal_app.models import Task
        
        task = await sync_to_async(Task.objects.select_related('goal').prefetch_related('tags').get)(
            id=task_id, creator=current_user
        )
        return await async_task_to_response(task)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="任务不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_active_user)
) -> TaskResponse:
    """创建新任务"""
    try:
        from goal_app.models import Task, Goal
        from goal_app.models import Tag as GoalTag
        
        # 验证目标是否存在（如果提供了goal_id）
        goal = None
        if task_data.goal_id:
            goal = await sync_to_async(sync_get_goal)(task_data.goal_id, current_user)
            if not goal:
                raise HTTPException(status_code=404, detail="关联的目标不存在")
        
        # 创建任务
        task = await sync_to_async(Task.objects.create)(
            name=task_data.name,
            description=task_data.description,
            goal=goal,
            status=task_data.status,
            priority=task_data.priority,
            urgency=task_data.urgency,
            creator=current_user
        )
        
        # 添加标签
        if task_data.tags:
            tags = await sync_to_async(list)(GoalTag.objects.filter(
                id__in=task_data.tags, creator=current_user
            ))
            await sync_to_async(task.tags.set)(tags)
        
        # 重新获取以包含所有关系
        task = await sync_to_async(Task.objects.select_related('goal').prefetch_related('tags').get)(id=task.id)
        return await async_task_to_response(task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_active_user)
) -> TaskResponse:
    """更新任务"""
    try:
        from goal_app.models import Task, Goal
        from goal_app.models import Tag as GoalTag
        
        task = await sync_to_async(Task.objects.select_related('goal').prefetch_related('tags').get)(
            id=task_id, creator=current_user
        )
        
        # 更新字段
        update_fields = {}
        if task_data.name is not None:
            update_fields['name'] = task_data.name
        if task_data.description is not None:
            update_fields['description'] = task_data.description
        if task_data.status is not None:
            update_fields['status'] = task_data.status
        if task_data.priority is not None:
            update_fields['priority'] = task_data.priority
        if task_data.urgency is not None:
            update_fields['urgency'] = task_data.urgency
        
        # 处理目标更新
        if task_data.goal_id is not None:
            if task_data.goal_id == 0:  # 特殊值表示清空关联
                update_fields['goal'] = None
            else:
                # 修复：使用 sync_to_async 包装同步的目标获取操作
                goal = await sync_to_async(sync_get_goal)(task_data.goal_id, current_user)
                if not goal:
                    raise HTTPException(status_code=404, detail="关联的目标不存在")
                update_fields['goal'] = goal
        
        # 执行更新
        for field, value in update_fields.items():
            setattr(task, field, value)
        await sync_to_async(task.save)()
        
        # 更新标签
        if task_data.tags is not None:
            tags = await sync_to_async(list)(GoalTag.objects.filter(
                id__in=task_data.tags, creator=current_user
            ))
            await sync_to_async(task.tags.set)(tags)
        
        # 重新获取以包含所有关系
        task = await sync_to_async(Task.objects.select_related('goal').prefetch_related('tags').get)(id=task.id)
        return await async_task_to_response(task)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """删除任务"""
    try:
        from goal_app.models import Task
        
        task = await sync_to_async(Task.objects.get)(
            id=task_id, creator=current_user
        )
        
        await sync_to_async(task.delete)()
        
        return None
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="任务不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")