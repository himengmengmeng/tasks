"""
Core email service: word selection, LLM story generation, and email sending.

Pattern: sync functions for ORM, wrapped with sync_to_async for async callers.
"""
import os
import logging
import random
from datetime import datetime

from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()
logger = logging.getLogger(__name__)

_story_llm = None


def get_story_llm():
    """Get or create the LLM instance for story generation (DeepSeek)."""
    global _story_llm
    if _story_llm is None:
        _story_llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.8,
            streaming=False,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
    return _story_llm


# ==================== Sync ORM Functions ====================

def select_random_words_sync(user_id: int, count: int = 3, exclude_ids: list = None):
    """Select random words from the user's vocabulary (sync, for ORM)."""
    from main_app.models import EnglishWord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if exclude_ids is None:
        exclude_ids = [22, 23]

    user = User.objects.get(id=user_id)
    queryset = EnglishWord.objects.filter(creator=user).exclude(id__in=exclude_ids)
    total = queryset.count()

    if total == 0:
        return []

    actual_count = min(count, total)
    words = list(queryset.order_by('?')[:actual_count])

    return [
        {"id": w.id, "title": w.title, "explanation": w.explanation}
        for w in words
    ]


def save_story_email_sync(user_id: int, word_dicts: list, story: str,
                          subject: str, recipient_emails: list, status: str,
                          error_message: str = None):
    """Save a StoryEmail record (sync, for ORM)."""
    from main_app.models import StoryEmail, EnglishWord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = User.objects.get(id=user_id)

    email_record = StoryEmail.objects.create(
        user=user,
        word_snapshots=[{"title": w["title"], "explanation": w["explanation"]} for w in word_dicts],
        story_content=story or "",
        subject=subject,
        recipient_emails=recipient_emails,
        status=status,
        error_message=error_message,
    )

    word_ids = [w["id"] for w in word_dicts if "id" in w]
    if word_ids:
        words = EnglishWord.objects.filter(id__in=word_ids)
        email_record.words.set(words)

    return email_record


def get_email_config_sync(user_id: int):
    """Get or create the EmailScheduleConfig for a user (sync)."""
    from main_app.models import EmailScheduleConfig
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = User.objects.get(id=user_id)
    config, _ = EmailScheduleConfig.objects.get_or_create(
        user=user,
        defaults={
            'is_active': False,
            'send_times': [],
            'exclude_word_ids': [22, 23],
        }
    )
    return config


def send_email_sync(subject: str, html_content: str, recipient_list: list):
    """Send an HTML email via Django's email backend (sync)."""
    from django.core.mail import send_mail
    from django.conf import settings

    send_mail(
        subject=subject,
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_content,
        fail_silently=False,
    )


# ==================== Async Functions ====================

async def generate_story(words: list[dict], language: str = "english") -> str:
    """Call LLM to generate a short story incorporating the given words."""
    word_list_text = "\n".join(
        f"- {w['title']}: {w['explanation']}" for w in words
    )

    if language == "bilingual":
        lang_instruction = (
            "Write the story in English first, then provide a Chinese translation below it. "
            "Separate them with a line '---'."
        )
    else:
        lang_instruction = "Write the story in English."

    prompt = f"""Write a short, engaging story (150-250 words) that naturally incorporates ALL of the following English words/phrases. **Bold** each target word/phrase when it first appears in the story.

{lang_instruction}

Words/phrases to include:
{word_list_text}

Requirements:
- The story should be interesting and memorable to help language learners remember these words.
- Use each word/phrase at least once, in a natural context that illustrates its meaning.
- Keep the tone friendly and vivid.
"""

    llm = get_story_llm()
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content


def build_email_html(word_dicts: list, story: str, sent_time: str) -> str:
    """Build an HTML email body with the story, vocabulary list, and timestamp."""
    words_html = ""
    for w in word_dicts:
        words_html += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;font-weight:600;color:#1a73e8;">{w['title']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;color:#333;">{w['explanation']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
<div style="max-width:600px;margin:20px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

  <div style="background:linear-gradient(135deg,#1a73e8,#4285f4);padding:24px 32px;">
    <h1 style="margin:0;color:#fff;font-size:22px;">Vocabulary Story of the Day</h1>
    <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">{sent_time}</p>
  </div>

  <div style="padding:24px 32px;">
    <h2 style="margin:0 0 12px;font-size:16px;color:#333;">Today's Words</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <tr style="background:#f8f9fa;">
        <th style="padding:8px 12px;text-align:left;font-size:13px;color:#666;border-bottom:2px solid #1a73e8;">Word / Phrase</th>
        <th style="padding:8px 12px;text-align:left;font-size:13px;color:#666;border-bottom:2px solid #1a73e8;">Meaning</th>
      </tr>
      {words_html}
    </table>

    <h2 style="margin:0 0 12px;font-size:16px;color:#333;">Story</h2>
    <div style="line-height:1.7;color:#444;font-size:15px;background:#fafbfc;padding:16px;border-radius:8px;border-left:4px solid #1a73e8;">
      {story.replace(chr(10), '<br>')}
    </div>
  </div>

  <div style="padding:16px 32px;background:#f8f9fa;text-align:center;font-size:12px;color:#999;">
    Goals &amp; Vocabulary App &mdash; Keep learning every day!
  </div>

</div>
</body>
</html>"""


async def send_story_email(user_id: int) -> dict:
    """
    Full pipeline: select words -> generate story -> send email -> save record.
    Returns a dict with status info.
    """
    config = await sync_to_async(get_email_config_sync)(user_id)

    word_dicts = await sync_to_async(select_random_words_sync)(
        user_id,
        count=config.words_per_email,
        exclude_ids=config.exclude_word_ids,
    )

    if not word_dicts:
        return {"status": "failed", "error": "No words available for this user"}

    recipients = await sync_to_async(config.get_all_recipients)()
    sent_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    titles = [w["title"] for w in word_dicts]
    subject = f"Vocabulary Story: {', '.join(titles)}"

    try:
        story = await generate_story(word_dicts, language=config.story_language)
        html_content = build_email_html(word_dicts, story, sent_time)
        await sync_to_async(send_email_sync)(subject, html_content, recipients)

        record = await sync_to_async(save_story_email_sync)(
            user_id, word_dicts, story, subject, recipients, "sent"
        )

        logger.info(f"Story email sent to {recipients} for user {user_id}")
        return {"status": "sent", "email_id": record.id, "subject": subject}

    except Exception as e:
        logger.error(f"Failed to send story email for user {user_id}: {e}", exc_info=True)

        story_text = ""
        try:
            story_text = story
        except NameError:
            pass

        await sync_to_async(save_story_email_sync)(
            user_id, word_dicts, story_text, subject, recipients, "failed", str(e)
        )

        return {"status": "failed", "error": str(e)}
