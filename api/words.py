# === words.py - 修复更新函数的异步问题 ===
from typing import TYPE_CHECKING, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from pydantic import BaseModel
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from asgiref.sync import sync_to_async
import os
from django.core.files.base import ContentFile
from .auth import get_current_active_user

# 🎯 类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()

router = APIRouter()

# Pydantic 模型
class WordBase(BaseModel):
    title: str
    explanation: str
    notes: Optional[str] = None

class WordCreate(WordBase):
    tags: Optional[List[int]] = []

class WordUpdate(BaseModel):
    title: Optional[str] = None
    explanation: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[int]] = None

class WordResponse(WordBase):
    id: int
    creator_id: int
    created_at: datetime
    tags: List[str] = []
    media_files: List[str] = []
    
    class Config:
        from_attributes = True

class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int
    page: int
    size: int

class MediaFileResponse(BaseModel):
    id: int
    file_url: str
    uploaded_at: datetime

# 异步查询函数
async def async_get_words(queryset, skip: int, limit: int):
    """异步执行单词查询"""
    total = await sync_to_async(queryset.count)()
    words = await sync_to_async(list)(queryset.order_by('-created_at')[skip:skip + limit])
    return words, total

async def async_word_to_response(word) -> WordResponse:
    """异步将 Django EnglishWord 模型转换为 Pydantic 响应模型"""
    # 异步获取标签
    tags_queryset = word.tags.all()
    tag_names = await sync_to_async(list)(tags_queryset.values_list('name', flat=True))
    
    # 异步获取媒体文件
    media_queryset = word.media_files.all()
    media_files = await sync_to_async(list)(media_queryset.values_list('file', flat=True))
    
    return WordResponse(
        id=word.id,
        title=word.title,
        explanation=word.explanation,
        notes=word.notes,
        creator_id=word.creator_id,
        created_at=word.created_at,
        tags=tag_names,
        media_files=media_files
    )

# 修复：创建同步函数来处理文件保存
def sync_create_media_file(word, filename, file_content):
    """同步函数：创建媒体文件记录"""
    from main_app.models import EnglishWordMedia
    media_file = EnglishWordMedia(word=word)
    media_file.file.save(filename, ContentFile(file_content))
    media_file.save()
    return media_file

# 修复：创建同步函数来检查标题是否存在
def sync_check_title_exists(title, creator, exclude_id=None):
    """同步函数：检查标题是否已存在"""
    from main_app.models import EnglishWord
    queryset = EnglishWord.objects.filter(title=title, creator=creator)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    return queryset.exists()

@router.get("/", response_model=WordListResponse)
async def list_words(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索单词标题"),
    tag_id: Optional[int] = Query(None, description="按标签ID过滤"),
    current_user: User = Depends(get_current_active_user)
) -> WordListResponse:
    """获取单词列表"""
    try:
        from main_app.models import EnglishWord
        
        # 构建查询
        queryset = EnglishWord.objects.filter(creator=current_user)
        
        # 应用过滤器
        if search:
            queryset = queryset.filter(title__icontains=search)
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)
        
        # 预取相关对象
        queryset = queryset.select_related('creator').prefetch_related('tags', 'media_files')
        
        # 使用异步方式获取数据
        words, total = await async_get_words(queryset, skip, limit)
        
        # 异步转换为响应模型
        word_responses = []
        for word in words:
            response = await async_word_to_response(word)
            word_responses.append(response)
        
        return WordListResponse(
            words=word_responses,
            total=total,
            page=skip // limit + 1,
            size=len(word_responses)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取单词列表失败: {str(e)}")

@router.get("/{word_id}", response_model=WordResponse)
async def get_word(
    word_id: int,
    current_user: User = Depends(get_current_active_user)
) -> WordResponse:
    """获取单个单词详情"""
    try:
        from main_app.models import EnglishWord
        
        word = await sync_to_async(EnglishWord.objects.select_related('creator').prefetch_related('tags', 'media_files').get)(
            id=word_id, creator=current_user
        )
        return await async_word_to_response(word)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="单词不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取单词失败: {str(e)}")

@router.post("/", response_model=WordResponse, status_code=status.HTTP_201_CREATED)
async def create_word(
    word_data: WordCreate,
    current_user: User = Depends(get_current_active_user)
) -> WordResponse:
    """创建新单词"""
    try:
        from main_app.models import EnglishWord
        from main_app.models import Tag as WordTag
        
        # 检查单词标题是否已存在（对同一用户）
        title_exists = await sync_to_async(sync_check_title_exists)(
            word_data.title, current_user
        )
        if title_exists:
            raise HTTPException(status_code=400, detail="单词标题已存在")
        
        # 创建单词
        word = await sync_to_async(EnglishWord.objects.create)(
            title=word_data.title,
            explanation=word_data.explanation,
            notes=word_data.notes,
            creator=current_user
        )
        
        # 添加标签
        if word_data.tags:
            tags = await sync_to_async(list)(WordTag.objects.filter(
                id__in=word_data.tags, creator=current_user
            ))
            await sync_to_async(word.tags.set)(tags)
        
        # 重新获取以包含所有关系
        word = await sync_to_async(EnglishWord.objects.select_related('creator').prefetch_related('tags', 'media_files').get)(id=word.id)
        return await async_word_to_response(word)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建单词失败: {str(e)}")

@router.put("/{word_id}", response_model=WordResponse)
async def update_word(
    word_id: int,
    word_data: WordUpdate,
    current_user: User = Depends(get_current_active_user)
) -> WordResponse:
    """更新单词"""
    try:
        from main_app.models import EnglishWord
        from main_app.models import Tag as WordTag
        
        word = await sync_to_async(EnglishWord.objects.select_related('creator').prefetch_related('tags', 'media_files').get)(
            id=word_id, creator=current_user
        )
        
        # 更新字段
        update_fields = {}
        if word_data.title is not None:
            # 检查新标题是否与其他单词冲突
            if word_data.title != word.title:
                title_exists = await sync_to_async(sync_check_title_exists)(
                    word_data.title, current_user, word_id
                )
                if title_exists:
                    raise HTTPException(status_code=400, detail="单词标题已存在")
            update_fields['title'] = word_data.title
        if word_data.explanation is not None:
            update_fields['explanation'] = word_data.explanation
        if word_data.notes is not None:
            update_fields['notes'] = word_data.notes
        
        # 执行更新
        for field, value in update_fields.items():
            setattr(word, field, value)
        await sync_to_async(word.save)()
        
        # 更新标签
        if word_data.tags is not None:
            tags = await sync_to_async(list)(WordTag.objects.filter(
                id__in=word_data.tags, creator=current_user
            ))
            await sync_to_async(word.tags.set)(tags)
        
        # 重新获取以包含所有关系
        word = await sync_to_async(EnglishWord.objects.select_related('creator').prefetch_related('tags', 'media_files').get)(id=word.id)
        return await async_word_to_response(word)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="单词不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新单词失败: {str(e)}")

@router.delete("/{word_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_word(
    word_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """删除单词"""
    try:
        from main_app.models import EnglishWord
        
        word = await sync_to_async(EnglishWord.objects.get)(
            id=word_id, creator=current_user
        )
        
        await sync_to_async(word.delete)()
        
        return None
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="单词不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除单词失败: {str(e)}")

@router.post("/{word_id}/media", response_model=MediaFileResponse)
async def upload_media_file(
    word_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
) -> MediaFileResponse:
    """为单词上传媒体文件"""
    try:
        from main_app.models import EnglishWord
        
        # 验证单词存在且属于当前用户
        word = await sync_to_async(EnglishWord.objects.get)(
            id=word_id, creator=current_user
        )
        
        # 验证文件类型
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'mp4', 'avi', 'mov', 'pdf', 'doc', 'docx', 'xls', 'xlsx']
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。允许的类型: {', '.join(allowed_extensions)}"
            )
        
        # 读取文件内容
        file_content = await file.read()
        
        # 修复：使用 sync_to_async 包装同步的文件保存操作
        media_file = await sync_to_async(sync_create_media_file)(
            word, 
            file.filename, 
            file_content
        )
        
        # 获取文件的URL
        file_url = media_file.file.url
        
        return MediaFileResponse(
            id=media_file.id,
            file_url=file_url,
            uploaded_at=media_file.uploaded_at
        )
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="单词不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传媒体文件失败: {str(e)}")

@router.delete("/{word_id}/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_file(
    word_id: int,
    media_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """删除单词的媒体文件"""
    try:
        from main_app.models import EnglishWord, EnglishWordMedia
        
        # 验证单词存在且属于当前用户
        word = await sync_to_async(EnglishWord.objects.get)(
            id=word_id, creator=current_user
        )
        
        # 验证媒体文件存在且属于该单词
        media_file = await sync_to_async(EnglishWordMedia.objects.get)(
            id=media_id, word=word
        )
        
        # 删除媒体文件（Django信号会自动删除实际文件）
        await sync_to_async(media_file.delete)()
        
        return None
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除媒体文件失败: {str(e)}")