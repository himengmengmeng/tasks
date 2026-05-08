"""
Core email service: word selection, LLM story generation, and email sending.

Pattern: sync functions for ORM, wrapped with sync_to_async for async callers.
"""
import html
import os
import logging
import random
import re
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
    from email.utils import formataddr
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings

    addr = settings.DEFAULT_FROM_EMAIL
    name = (getattr(settings, 'EMAIL_SENDER_NAME', '') or '').strip()
    from_email = formataddr((name, addr)) if name else addr

    plain_fallback = "Open this email in an HTML-capable client to read your vocabulary story."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_fallback,
        from_email=from_email,
        to=recipient_list,
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=False)


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

    prompt = f"""Write a short, engaging story (150-250 words) that naturally incorporates ALL of the following English words/phrases. Emphasize each target word/phrase when it first appears (plain wording only).

{lang_instruction}

Words/phrases to include:
{word_list_text}

Requirements:
- The story should be interesting and memorable to help language learners remember these words.
- Use each word/phrase at least once, in a natural context that illustrates its meaning.
- Keep the tone friendly and vivid.
- Do NOT use markdown: no ** asterisks, no *italics* markup, no HTML tags.
"""

    llm = get_story_llm()
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content


def _pattern_for_vocab_title(title: str) -> re.Pattern:
    """Match a vocabulary title; use word boundaries for single-token titles to reduce false positives."""
    t = (title or "").strip()
    if not t:
        return re.compile("$^")
    if " " in t or re.search(r"[\u4e00-\u9fff]", t):
        return re.compile(re.escape(t), re.IGNORECASE)
    return re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)", re.IGNORECASE)


def _highlight_vocab_in_plain_text(text: str, word_dicts: list, accent_hex: str) -> str:
    """Escape plain text and wrap vocabulary titles (case-insensitive) in themed spans."""
    if not text:
        return ""
    titles = sorted(
        {((w.get("title") or "").strip()) for w in word_dicts if (w.get("title") or "").strip()},
        key=len,
        reverse=True,
    )
    if not titles:
        return html.escape(text)

    tokens: dict[str, str] = {}
    state = {"n": 0}
    s = text
    for title in titles:
        pattern = _pattern_for_vocab_title(title)

        def repl(m: re.Match) -> str:
            k = f"\u27e6VOC_{state['n']}\u27e7"
            tokens[k] = m.group(0)
            state["n"] += 1
            return k

        s = pattern.sub(repl, s)

    s_esc = html.escape(s)
    for key, original in tokens.items():
        inner = html.escape(original)
        span = (
            f'<span class="story-vocab" style="color:{accent_hex};font-weight:700;">'
            f"{inner}</span>"
        )
        s_esc = s_esc.replace(html.escape(key), span)
    return s_esc


def _story_to_email_html_fragment(
    story: str, word_dicts: list | None = None, vocab_accent: str = "#38aaf8"
) -> str:
    """Turn LLM story into safe HTML: **bold** → <strong>, highlight vocab in theme color, preserve line breaks."""
    raw = story or ""
    # Remove standalone markdown divider lines (bilingual stories).
    # Avoid (?<=...) with |^ — Python re requires fixed-width lookbehind.
    raw = re.sub(r"^\s*---\s*$", "", raw, flags=re.MULTILINE)
    wd = word_dicts or []
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"\*\*(.+?)\*\*", raw, flags=re.DOTALL):
        parts.append(_highlight_vocab_in_plain_text(raw[last:m.start()], wd, vocab_accent))
        inner_raw = m.group(1).strip()
        inner_html = _highlight_vocab_in_plain_text(inner_raw, wd, vocab_accent)
        parts.append(
            '<strong style="color:#7dc8fc;font-weight:600;">'
            f"{inner_html}"
            "</strong>"
        )
        last = m.end()
    tail = raw[last:].replace("**", "")
    parts.append(_highlight_vocab_in_plain_text(tail, wd, vocab_accent))
    return "".join(parts).replace("\n", "<br>\n")


def build_email_html(word_dicts: list, story: str, sent_time: str) -> str:
    """Build a mobile-friendly HTML email matching Goal App (Tailwind primary / dark palette)."""
    from django.conf import settings

    esc = html.escape
    sender_label = esc(
        (getattr(settings, "EMAIL_SENDER_NAME", None) or "Goal App").strip() or "Goal App"
    )
    # Goal App — tailwind.config.js primary + dark
    c_bg = "#121316"
    c_shell = "#1e1f23"
    c_border = "#35373c"
    c_text = "#e2e3e5"
    c_muted = "#9fa2a9"
    c_accent = "#38aaf8"
    c_accent_mid = "#0e8de9"
    c_accent_deep = "#026fc7"

    words_html = ""
    for w in word_dicts:
        title = esc(w.get("title", "") or "")
        expl = esc(w.get("explanation", "") or "")
        words_html += f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 12px;border-collapse:separate;">
        <tr>
          <td class="word-card" style="background-color:#24252a;border:1px solid {c_border};border-radius:12px;padding:14px 16px;">
            <p class="word-title" style="margin:0 0 6px;font-size:16px;font-weight:700;color:{c_accent};line-height:1.35;word-break:break-word;">
              {title}
            </p>
            <p class="word-meaning" style="margin:0;font-size:15px;color:{c_text};line-height:1.55;word-break:break-word;opacity:0.95;">
              {expl}
            </p>
          </td>
        </tr>
      </table>
"""

    story_safe = _story_to_email_html_fragment(story, word_dicts, c_accent)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Vocabulary story</title>
  <style type="text/css">
    html, body {{ margin:0 !important; padding:0 !important; height:100% !important; width:100% !important; }}
    * {{ -ms-text-size-adjust:100%; -webkit-text-size-adjust:100%; }}
    table, td {{ mso-table-lspace:0pt; mso-table-rspace:0pt; }}
    img {{ -ms-interpolation-mode:bicubic; border:0; height:auto; line-height:100%; }}
    @media only screen and (max-width: 620px) {{
      .wrapper {{ width:100% !important; max-width:100% !important; }}
      .shell {{ border-radius:0 !important; margin:0 !important; border-left:none !important; border-right:none !important; }}
      .pad-header {{ padding:18px 20px !important; }}
      .pad-body {{ padding:18px 16px !important; }}
      .pad-footer {{ padding:14px 16px !important; }}
      .hero-title {{ font-size:20px !important; line-height:1.25 !important; }}
      .section-title {{ font-size:15px !important; }}
      .story-box {{ font-size:15px !important; padding:14px !important; }}
      .word-card {{ padding:12px 14px !important; }}
      .word-title {{ font-size:15px !important; }}
      .word-meaning {{ font-size:14px !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:{c_bg};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="wrapper" style="background-color:{c_bg};">
    <tr>
      <td align="center" style="padding:16px 10px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" class="shell wrapper" style="max-width:600px;background-color:{c_shell};border-radius:16px;overflow:hidden;border:1px solid {c_border};box-shadow:0 8px 32px rgba(0,0,0,0.35);">
          <tr>
            <td class="pad-header" style="background:linear-gradient(135deg,{c_accent} 0%,{c_accent_mid} 45%,{c_accent_deep} 100%);padding:22px 26px;">
              <p style="margin:0 0 4px;font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.85);font-family:'DM Sans','Segoe UI',Roboto,system-ui,sans-serif;">
                Goal App
              </p>
              <h1 class="hero-title" style="margin:0;color:#ffffff;font-size:21px;font-weight:700;line-height:1.3;font-family:'DM Sans','Segoe UI',Roboto,system-ui,sans-serif;">
                Vocabulary story of the day
              </h1>
              <p style="margin:8px 0 0;color:rgba(255,255,255,0.88);font-size:13px;font-family:'DM Sans','Segoe UI',Roboto,system-ui,sans-serif;">
                {esc(sent_time)}
              </p>
            </td>
          </tr>
          <tr>
            <td class="pad-body" style="padding:22px 24px;font-family:'DM Sans','Segoe UI',Roboto,system-ui,sans-serif;background-color:{c_shell};">
              <h2 class="section-title" style="margin:0 0 14px;font-size:16px;color:{c_text};font-weight:700;">Today's words</h2>
              {words_html}
              <h2 class="section-title" style="margin:20px 0 12px;font-size:16px;color:{c_text};font-weight:700;">Story</h2>
              <div class="story-box" style="line-height:1.65;color:{c_text};font-size:16px;background-color:#121316;padding:18px;border-radius:12px;border:1px solid {c_border};border-left:4px solid {c_accent_mid};word-break:break-word;overflow-wrap:break-word;">
                {story_safe}
              </div>
            </td>
          </tr>
          <tr>
            <td class="pad-footer" style="padding:16px 24px;background-color:#121316;text-align:center;font-size:12px;color:{c_muted};line-height:1.5;font-family:'DM Sans','Segoe UI',Roboto,system-ui,sans-serif;border-top:1px solid {c_border};">
              Sent by <strong style="color:{c_accent};font-weight:600;">{sender_label}</strong> &mdash; keep learning every day!
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
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
