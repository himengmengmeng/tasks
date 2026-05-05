# === goals.py 的完整版本 ===
from typing import TYPE_CHECKING, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
from .auth import get_current_active_user


# 🎯 专业类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()

router = APIRouter()

# Pydantic 模型
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
async def async_goal_to_response(goal) -> GoalResponse:
    """异步将 Django Goal 模型转换为 Pydantic 响应模型"""
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
        creator_id=goal.creator_id,
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
    status: Optional[List[str]] = Query(None, description="按状态过滤(可多选)"),
    priority: Optional[List[str]] = Query(None, description="按优先级过滤(可多选)"),
    tag_id: Optional[List[int]] = Query(None, description="按标签ID过滤(可多选)"),
    current_user: User = Depends(get_current_active_user)
) -> GoalListResponse:
    """获取目标列表"""
    # 构建查询
    from goal_app.models import Goal
    queryset = Goal.objects.filter(creator=current_user)
    
    # 应用过滤器（支持多选）
    if status:
        queryset = queryset.filter(status__in=status)
    if priority:
        queryset = queryset.filter(priority__in=priority)
    if tag_id:
        queryset = queryset.filter(tags__id__in=tag_id).distinct()
    
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
        from goal_app.models import Goal
        
        # 异步获取目标
        goal = await sync_to_async(Goal.objects.select_related('creator').prefetch_related('tags').get)(
            id=goal_id, creator=current_user
        )
        return await async_goal_to_response(goal)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="目标不存在")

@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_active_user)
) -> GoalResponse:
    """创建新目标"""
    try:
        from goal_app.models import Goal
        from goal_app.models import Tag as GoalTag
        
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
            tags = await sync_to_async(list)(GoalTag.objects.filter(
                id__in=goal_data.tags, creator=current_user
            ))
            await sync_to_async(goal.tags.set)(tags)
        
        # 重新获取以包含所有关系
        goal = await sync_to_async(Goal.objects.select_related('creator').prefetch_related('tags').get)(id=goal.id)
        return await async_goal_to_response(goal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建目标失败: {str(e)}")

@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: int,
    goal_data: GoalUpdate,
    current_user: User = Depends(get_current_active_user)
) -> GoalResponse:
    """更新目标"""
    try:
        from goal_app.models import Goal
        from goal_app.models import Tag as GoalTag
        
        goal = await sync_to_async(Goal.objects.select_related('creator').prefetch_related('tags').get)(
            id=goal_id, creator=current_user
        )
        
        # 更新字段
        update_fields = {}
        if goal_data.title is not None:
            update_fields['title'] = goal_data.title
        if goal_data.description is not None:
            update_fields['description'] = goal_data.description
        if goal_data.notes is not None:
            update_fields['notes'] = goal_data.notes
        if goal_data.status is not None:
            update_fields['status'] = goal_data.status
        if goal_data.priority is not None:
            update_fields['priority'] = goal_data.priority
        if goal_data.urgency is not None:
            update_fields['urgency'] = goal_data.urgency
        
        # 执行更新
        for field, value in update_fields.items():
            setattr(goal, field, value)
        await sync_to_async(goal.save)()
        
        # 更新标签
        if goal_data.tags is not None:
            tags = await sync_to_async(list)(GoalTag.objects.filter(
                id__in=goal_data.tags, creator=current_user
            ))
            await sync_to_async(goal.tags.set)(tags)
        
        # 重新获取以包含所有关系
        goal = await sync_to_async(Goal.objects.select_related('creator').prefetch_related('tags').get)(id=goal.id)
        return await async_goal_to_response(goal)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="目标不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新目标失败: {str(e)}")

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """删除目标"""
    try:
        from goal_app.models import Goal
        
        goal = await sync_to_async(Goal.objects.get)(
            id=goal_id, creator=current_user
        )
        
        await sync_to_async(goal.delete)()
        
        return None
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="目标不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除目标失败: {str(e)}")