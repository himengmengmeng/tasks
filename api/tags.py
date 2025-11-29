
# === tags.py - 支持两种标签类型的完整版本 ===
from typing import TYPE_CHECKING, List, Optional, Literal
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
class TagBase(BaseModel):
    name: str
    tag_type: Literal['goals', 'words'] = 'goals'  # 标签类型：goals 或 words

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = None
    tag_type: Optional[Literal['goals', 'words']] = None

class TagResponse(TagBase):
    id: int
    creator_id: int
    created_at: datetime
    goal_count: int = 0
    task_count: int = 0
    word_count: int = 0
    
    class Config:
        from_attributes = True

class TagListResponse(BaseModel):
    tags: List[TagResponse]
    total: int
    page: int
    size: int

# 获取标签模型的辅助函数
async def get_tag_model(tag_type: str):
    """根据标签类型返回对应的Tag模型"""
    if tag_type == 'goals':
        try:
            from goal_app.models import Tag as GoalTag
            return GoalTag
        except ImportError:
            raise HTTPException(status_code=500, detail="Goal标签模型未找到")
    elif tag_type == 'words':
        try:
            from main_app.models import Tag as WordTag
            return WordTag
        except ImportError:
            raise HTTPException(status_code=500, detail="Word标签模型未找到")
    else:
        raise HTTPException(status_code=400, detail="不支持的标签类型")

# 异步查询函数
async def async_get_tags(queryset, skip: int, limit: int):
    """异步执行标签查询"""
    total = await sync_to_async(queryset.count)()
    tags = await sync_to_async(list)(queryset.order_by('-created_at')[skip:skip + limit])
    return tags, total

async def async_tag_to_response(tag, tag_type: str) -> TagResponse:
    """异步将 Django Tag 模型转换为 Pydantic 响应模型"""
    # 根据标签类型获取关联计数
    goal_count = 0
    task_count = 0
    word_count = 0
    
    if tag_type == 'goals':
        goal_count = await sync_to_async(tag.goals.count)()
        task_count = await sync_to_async(tag.tasks.count)()
    elif tag_type == 'words':
        word_count = await sync_to_async(tag.english_words.count)()
    
    return TagResponse(
        id=tag.id,
        name=tag.name,
        tag_type=tag_type,
        creator_id=tag.creator_id,
        created_at=tag.created_at,
        goal_count=goal_count,
        task_count=task_count,
        word_count=word_count
    )

@router.get("/", response_model=TagListResponse)
async def list_tags(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索标签名称"),
    tag_type: Optional[Literal['goals', 'words']] = Query(None, description="标签类型"),
    current_user: User = Depends(get_current_active_user)
) -> TagListResponse:
    """获取标签列表 - 支持两种标签类型"""
    try:
        # 获取所有标签类型的数据
        all_tags = []
        total_count = 0
        
        # 处理 goals 标签
        if tag_type is None or tag_type == 'goals':
            try:
                from goal_app.models import Tag as GoalTag
                goal_queryset = GoalTag.objects.filter(creator=current_user)
                if search:
                    goal_queryset = goal_queryset.filter(name__icontains=search)
                
                goal_tags, goal_total = await async_get_tags(goal_queryset, skip, limit)
                for tag in goal_tags:
                    response = await async_tag_to_response(tag, 'goals')
                    all_tags.append(response)
                total_count += goal_total
            except ImportError:
                pass  # 如果goal_app不存在，跳过
        
        # 处理 words 标签
        if tag_type is None or tag_type == 'words':
            try:
                from main_app.models import Tag as WordTag
                word_queryset = WordTag.objects.filter(creator=current_user)
                if search:
                    word_queryset = word_queryset.filter(name__icontains=search)
                
                word_tags, word_total = await async_get_tags(word_queryset, skip, limit)
                for tag in word_tags:
                    response = await async_tag_to_response(tag, 'words')
                    all_tags.append(response)
                total_count += word_total
            except ImportError:
                pass  # 如果main_app不存在，跳过
        
        # 按创建时间排序
        all_tags.sort(key=lambda x: x.created_at, reverse=True)
        
        # 应用分页
        paginated_tags = all_tags[skip:skip + limit]
        
        return TagListResponse(
            tags=paginated_tags,
            total=total_count,
            page=skip // limit + 1,
            size=len(paginated_tags)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签列表失败: {str(e)}")

@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    tag_type: Literal['goals', 'words'] = Query(..., description="标签类型"),
    current_user: User = Depends(get_current_active_user)
) -> TagResponse:
    """获取单个标签详情 - 必须指定标签类型"""
    try:
        tag_model = await get_tag_model(tag_type)
        
        tag = await sync_to_async(tag_model.objects.get)(
            id=tag_id, creator=current_user
        )
        return await async_tag_to_response(tag, tag_type)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="标签不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取标签失败: {str(e)}")

@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_active_user)
) -> TagResponse:
    """创建新标签 - 根据tag_type创建对应的标签"""
    try:
        tag_model = await get_tag_model(tag_data.tag_type)
        
        # 检查标签名称是否已存在（对同一用户和同一类型）
        existing_tag = await sync_to_async(tag_model.objects.filter)(
            name=tag_data.name, creator=current_user
        )
        if await sync_to_async(existing_tag.exists)():
            raise HTTPException(status_code=400, detail="标签名称已存在")
        
        # 创建标签
        tag = await sync_to_async(tag_model.objects.create)(
            name=tag_data.name,
            creator=current_user
        )
        
        return await async_tag_to_response(tag, tag_data.tag_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建标签失败: {str(e)}")

@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    tag_type: Literal['goals', 'words'] = Query(..., description="标签类型"),
    current_user: User = Depends(get_current_active_user)
) -> TagResponse:
    """更新标签 - 必须指定标签类型"""
    try:
        tag_model = await get_tag_model(tag_type)
        
        tag = await sync_to_async(tag_model.objects.get)(
            id=tag_id, creator=current_user
        )
        
        # 更新字段
        update_fields = {}
        if tag_data.name is not None:
            # 检查新名称是否与其他标签冲突
            if tag_data.name != tag.name:
                existing_tag = await sync_to_async(tag_model.objects.filter)(
                    name=tag_data.name, creator=current_user
                ).exclude(id=tag_id)
                if await sync_to_async(existing_tag.exists)():
                    raise HTTPException(status_code=400, detail="标签名称已存在")
            update_fields['name'] = tag_data.name
        
        # 注意：不能通过API更改标签类型，因为涉及到不同的数据库表
        
        if update_fields:
            for field, value in update_fields.items():
                setattr(tag, field, value)
            await sync_to_async(tag.save)()
        
        return await async_tag_to_response(tag, tag_type)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="标签不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新标签失败: {str(e)}")

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    tag_type: Literal['goals', 'words'] = Query(..., description="标签类型"),
    current_user: User = Depends(get_current_active_user)
):
    """删除标签 - 必须指定标签类型"""
    try:
        tag_model = await get_tag_model(tag_type)
        
        tag = await sync_to_async(tag_model.objects.get)(
            id=tag_id, creator=current_user
        )
        
        await sync_to_async(tag.delete)()
        
        return None
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="标签不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除标签失败: {str(e)}")