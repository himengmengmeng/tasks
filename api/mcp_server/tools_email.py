"""MCP tools for Email Schedule Config management."""
import json
from asgiref.sync import sync_to_async


def _serialize_config(config, user_email: str):
    """Serialize an EmailScheduleConfig object to dict."""
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
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
    }


def _serialize_story_email(email_obj):
    """Serialize a StoryEmail object to dict."""
    return {
        "id": email_obj.id,
        "subject": email_obj.subject,
        "word_snapshots": email_obj.word_snapshots or [],
        "story_content": email_obj.story_content[:500],
        "recipient_emails": email_obj.recipient_emails or [],
        "sent_at": email_obj.sent_at.isoformat(),
        "status": email_obj.status,
    }


# ==================== Email Config Tools ====================

async def get_email_config(user_id: int) -> str:
    """Get the user's email schedule configuration."""
    from main_app.models import EmailScheduleConfig
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    def _get_or_create(u):
        config, _ = EmailScheduleConfig.objects.get_or_create(
            user=u,
            defaults={'is_active': False, 'send_times': [], 'exclude_word_ids': [22, 23]}
        )
        return config

    config = await sync_to_async(_get_or_create)(user)
    return json.dumps(_serialize_config(config, user.email), ensure_ascii=False)


async def update_email_config(
    user_id: int,
    is_active: bool = None,
    timezone: str = None,
    send_times: str = None,
    words_per_email: int = None,
    extra_recipients: str = None,
    story_language: str = None,
    exclude_word_ids: str = None,
) -> str:
    """Update the user's email schedule configuration.
    send_times: comma-separated HH:MM values, e.g. '08:00,18:00'.
    extra_recipients: comma-separated emails, max 3.
    exclude_word_ids: comma-separated integer IDs.
    """
    from main_app.models import EmailScheduleConfig
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    def _update(u):
        config, _ = EmailScheduleConfig.objects.get_or_create(
            user=u,
            defaults={'is_active': False, 'send_times': [], 'exclude_word_ids': [22, 23]}
        )
        if is_active is not None:
            config.is_active = is_active
        if timezone is not None:
            config.timezone = timezone
        if send_times is not None:
            config.send_times = [t.strip() for t in send_times.split(",") if t.strip()]
        if words_per_email is not None:
            config.words_per_email = max(1, min(5, words_per_email))
        if extra_recipients is not None:
            config.extra_recipients = [e.strip() for e in extra_recipients.split(",") if e.strip()][:3]
        if story_language is not None:
            config.story_language = story_language
        if exclude_word_ids is not None:
            config.exclude_word_ids = [int(x.strip()) for x in exclude_word_ids.split(",") if x.strip()]
        config.save()
        return config

    config = await sync_to_async(_update)(user)
    return json.dumps(
        {"message": "Email config updated successfully", "config": _serialize_config(config, user.email)},
        ensure_ascii=False,
    )


async def send_test_email(user_id: int) -> str:
    """Trigger an immediate test story email for the user."""
    from api.email_service import send_story_email
    result = await send_story_email(user_id)
    return json.dumps(result, ensure_ascii=False)


async def list_email_history(user_id: int, skip: int = 0, limit: int = 10) -> str:
    """List recently sent story emails for the user."""
    from main_app.models import StoryEmail
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    def _query(u):
        qs = StoryEmail.objects.filter(user=u).order_by('-sent_at')
        total = qs.count()
        emails = list(qs[skip:skip + limit])
        return emails, total

    emails, total = await sync_to_async(_query)(user)
    results = [_serialize_story_email(e) for e in emails]
    return json.dumps({"emails": results, "total": total}, ensure_ascii=False)
