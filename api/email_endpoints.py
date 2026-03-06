"""FastAPI endpoints for Email Schedule Config and Story Email history."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from datetime import datetime
from asgiref.sync import sync_to_async

from .auth import get_current_active_user
from .email_service import send_story_email

from django.contrib.auth import get_user_model
User = get_user_model()

router = APIRouter()


# ==================== Pydantic Schemas ====================

class EmailConfigSchema(BaseModel):
    is_active: Optional[bool] = None
    timezone: Optional[str] = None
    send_times: Optional[List[str]] = None
    words_per_email: Optional[int] = None
    extra_recipients: Optional[List[str]] = None
    story_language: Optional[str] = None
    exclude_word_ids: Optional[List[int]] = None


class EmailConfigResponse(BaseModel):
    id: int
    is_active: bool
    timezone: str
    send_times: List[str]
    words_per_email: int
    extra_recipients: List[str]
    story_language: str
    exclude_word_ids: List[int]
    user_email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoryEmailResponse(BaseModel):
    id: int
    word_snapshots: list
    story_content: str
    subject: str
    recipient_emails: list
    sent_at: datetime
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class StoryEmailListResponse(BaseModel):
    emails: List[StoryEmailResponse]
    total: int
    page: int
    size: int


# ==================== Sync ORM Helpers ====================

def _get_or_create_config_sync(user):
    from main_app.models import EmailScheduleConfig
    config, _ = EmailScheduleConfig.objects.get_or_create(
        user=user,
        defaults={
            'is_active': False,
            'send_times': [],
            'exclude_word_ids': [22, 23],
        }
    )
    return config


def _update_config_sync(user, data: dict):
    from main_app.models import EmailScheduleConfig
    config, _ = EmailScheduleConfig.objects.get_or_create(
        user=user,
        defaults={
            'is_active': False,
            'send_times': [],
            'exclude_word_ids': [22, 23],
        }
    )

    for field, value in data.items():
        if value is not None:
            setattr(config, field, value)

    config.save()
    return config


def _config_to_dict(config, user_email: str) -> dict:
    return {
        "id": config.id,
        "is_active": config.is_active,
        "timezone": config.timezone,
        "send_times": config.send_times or [],
        "words_per_email": config.words_per_email,
        "extra_recipients": config.extra_recipients or [],
        "story_language": config.story_language,
        "exclude_word_ids": config.exclude_word_ids or [],
        "user_email": user_email,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


def _list_history_sync(user, skip: int, limit: int):
    from main_app.models import StoryEmail
    queryset = StoryEmail.objects.filter(user=user).order_by('-sent_at')
    total = queryset.count()
    emails = list(queryset[skip:skip + limit])
    return emails, total


def _get_history_detail_sync(user, email_id: int):
    from main_app.models import StoryEmail
    try:
        return StoryEmail.objects.get(id=email_id, user=user)
    except StoryEmail.DoesNotExist:
        return None


def _email_to_dict(email_obj) -> dict:
    return {
        "id": email_obj.id,
        "word_snapshots": email_obj.word_snapshots or [],
        "story_content": email_obj.story_content,
        "subject": email_obj.subject,
        "recipient_emails": email_obj.recipient_emails or [],
        "sent_at": email_obj.sent_at,
        "status": email_obj.status,
        "error_message": email_obj.error_message,
    }


# ==================== Endpoints ====================

@router.get("/config", response_model=EmailConfigResponse)
async def get_email_config(current_user=Depends(get_current_active_user)):
    """Get the current user's email schedule configuration."""
    config = await sync_to_async(_get_or_create_config_sync)(current_user)
    return await sync_to_async(_config_to_dict)(config, current_user.email)


@router.put("/config", response_model=EmailConfigResponse)
async def update_email_config(
    data: EmailConfigSchema,
    current_user=Depends(get_current_active_user),
):
    """Create or update the user's email schedule configuration."""
    update_data = data.model_dump(exclude_unset=True)

    if "extra_recipients" in update_data and update_data["extra_recipients"] is not None:
        if len(update_data["extra_recipients"]) > 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 3 extra recipients allowed",
            )

    if "words_per_email" in update_data and update_data["words_per_email"] is not None:
        if not (1 <= update_data["words_per_email"] <= 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="words_per_email must be between 1 and 5",
            )

    config = await sync_to_async(_update_config_sync)(current_user, update_data)
    return await sync_to_async(_config_to_dict)(config, current_user.email)


@router.get("/history", response_model=StoryEmailListResponse)
async def list_email_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_active_user),
):
    """List sent story emails (paginated)."""
    emails, total = await sync_to_async(_list_history_sync)(current_user, skip, limit)

    email_dicts = []
    for e in emails:
        email_dicts.append(await sync_to_async(_email_to_dict)(e))

    return {
        "emails": email_dicts,
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
    }


@router.get("/history/{email_id}", response_model=StoryEmailResponse)
async def get_email_detail(
    email_id: int,
    current_user=Depends(get_current_active_user),
):
    """Get details of a specific sent story email."""
    email_obj = await sync_to_async(_get_history_detail_sync)(current_user, email_id)
    if not email_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email with id {email_id} not found",
        )
    return await sync_to_async(_email_to_dict)(email_obj)


@router.post("/test-send")
async def test_send_email(current_user=Depends(get_current_active_user)):
    """Trigger an immediate test story email for the current user."""
    result = await send_story_email(current_user.id)

    if result["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to send email"),
        )

    return {"message": "Test email sent successfully", **result}
