# === goals.py 的 TYPE_CHECKING 版本 ===
from typing import TYPE_CHECKING, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
from .auth import get_current_active_user
from goal_app.models import Goal, Tag


# 🎯 专业类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()

router = APIRouter()

# Pydantic 模型（保持不变）
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    notes: Optional[str] = None
    status: str = "not_started"
    priority: str = "medium"
    urgency: str = "medium"

class GoalCreate(GoalBase):
    tags: Optional[List[int]] = []

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    urgency: Optional[str] = None
    tags: Optional[List[int]] = None

class GoalResponse(GoalBase):
    id: int
    creator_id: int
    created_time: datetime
    tags: List[str] = []
    
    class Config:
        from_attributes = True

class GoalListResponse(BaseModel):
    goals: List[GoalResponse]
    total: int
    page: int
    size: int

# 创建异步的 goal_to_response 函数
async def async_goal_to_response(goal: Goal) -> GoalResponse:
    """异步将 Django Goal 模型转换为 Pydantic 响应模型"""
    # 预取相关对象以避免 N+1 查询
    creator_id = goal.creator_id  # 直接使用外键字段，避免额外查询
    
    # 异步获取标签
    tags_queryset = goal.tags.all()
    tag_names = await sync_to_async(list)(tags_queryset.values_list('name', flat=True))
    
    return GoalResponse(
        id=goal.id,
        title=goal.title,
        description=goal.description,
        notes=goal.notes,
        status=goal.status,
        priority=goal.priority,
        urgency=goal.urgency,
        creator_id=creator_id,  # 使用预取的外键
        created_time=goal.created_time,
        tags=tag_names
    )

# 创建异步查询函数
async def async_get_goals(queryset, skip: int, limit: int):
    """异步执行查询并预取相关对象"""
    # 使用 select_related 和 prefetch_related 避免 N+1 查询
    queryset = queryset.select_related('creator').prefetch_related('tags')
    
    total = await sync_to_async(queryset.count)()
    goals = await sync_to_async(list)(queryset.order_by('-created_time')[skip:skip + limit])
    return goals, total

@router.get("/", response_model=GoalListResponse)
async def list_goals(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    priority: Optional[str] = Query(None, description="按优先级过滤"),
    current_user: User = Depends(get_current_active_user)
) -> GoalListResponse:
    """fetch goals with optional filters"""
    # 构建查询
    queryset = Goal.objects.filter(creator=current_user)
    
    # 应用过滤器
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    
    # 使用异步方式获取数据
    goals, total = await async_get_goals(queryset, skip, limit)
    
    # 异步转换为响应模型
    goal_responses = []
    for goal in goals:
        response = await async_goal_to_response(goal)
        goal_responses.append(response)
    
    return GoalListResponse(
        goals=goal_responses,
        total=total,
        page=skip // limit + 1,
        size=len(goal_responses)
    )

# 其他 CRUD 操作也需要类似的异步包装
@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user)
) -> GoalResponse:
    """获取单个目标详情"""
    try:
        # 异步获取目标
        goal = await sync_to_async(Goal.objects.select_related('creator').prefetch_related('tags').get)(
            id=goal_id, creator=current_user
        )
        return await async_goal_to_response(goal)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="Goal doesn't exist")

@router.post("/", response_model=GoalResponse)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_active_user)
) -> GoalResponse:
    """创建新目标"""
    # 异步创建目标
    goal = await sync_to_async(Goal.objects.create)(
        title=goal_data.title,
        description=goal_data.description,
        notes=goal_data.notes,
        status=goal_data.status,
        priority=goal_data.priority,
        urgency=goal_data.urgency,
        creator=current_user
    )
    
    # 异步添加标签
    if goal_data.tags:
        tags = await sync_to_async(list)(Tag.objects.filter(id__in=goal_data.tags))
        await sync_to_async(goal.tags.set)(tags)
    
    # 重新获取以包含所有关系
    goal = await sync_to_async(Goal.objects.select_related('creator').prefetch_related('tags').get)(id=goal.id)
    return await async_goal_to_response(goal)