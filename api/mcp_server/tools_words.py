"""MCP tools for English Words and Word Tags CRUD operations."""
import json
from asgiref.sync import sync_to_async


def _serialize_word(word, tag_names):
    """Serialize an EnglishWord object to dict."""
    return {
        "id": word.id,
        "title": word.title,
        "explanation": word.explanation,
        "notes": word.notes or "",
        "created_at": word.created_at.isoformat(),
        "tags": tag_names,
    }


def _serialize_word_tag(tag, word_count=0):
    """Serialize a Word Tag object to dict."""
    return {
        "id": tag.id,
        "name": tag.name,
        "created_at": tag.created_at.isoformat(),
        "word_count": word_count,
    }


# ==================== Word Tools ====================

async def list_words(user_id: int, search: str = None, tag_id: int = None,
                     skip: int = 0, limit: int = 20) -> str:
    """List English words for the user with optional filters."""
    from main_app.models import EnglishWord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    queryset = EnglishWord.objects.filter(creator=user).prefetch_related('tags')

    if search:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(explanation__icontains=search) |
            Q(notes__icontains=search)
        )
    if tag_id:
        queryset = queryset.filter(tags__id=tag_id)

    total = await sync_to_async(queryset.count)()
    words = await sync_to_async(list)(queryset.order_by('-created_at')[skip:skip + limit])

    results = []
    for word in words:
        tag_names = await sync_to_async(list)(word.tags.values_list('name', flat=True))
        results.append(_serialize_word(word, tag_names))

    return json.dumps({"words": results, "total": total}, ensure_ascii=False)


async def get_word(user_id: int, word_id: int) -> str:
    """Get a specific English word by ID."""
    from main_app.models import EnglishWord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        word = await sync_to_async(
            EnglishWord.objects.prefetch_related('tags').get
        )(id=word_id, creator=user)
        tag_names = await sync_to_async(list)(word.tags.values_list('name', flat=True))
        return json.dumps(_serialize_word(word, tag_names), ensure_ascii=False)
    except EnglishWord.DoesNotExist:
        return json.dumps({"error": f"Word with id {word_id} not found"})


async def create_word(user_id: int, title: str, explanation: str, notes: str = "",
                      tag_ids: list = None) -> str:
    """Create a new English word."""
    from main_app.models import EnglishWord, Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    exists = await sync_to_async(EnglishWord.objects.filter(title=title, creator=user).exists)()
    if exists:
        return json.dumps({"error": f"Word '{title}' already exists"})

    word = await sync_to_async(EnglishWord.objects.create)(
        title=title,
        explanation=explanation,
        notes=notes or None,
        creator=user
    )

    if tag_ids:
        tags = await sync_to_async(list)(WordTag.objects.filter(id__in=tag_ids, creator=user))
        await sync_to_async(word.tags.set)(tags)

    word = await sync_to_async(
        EnglishWord.objects.prefetch_related('tags').get
    )(id=word.id)
    tag_names = await sync_to_async(list)(word.tags.values_list('name', flat=True))
    return json.dumps({"message": "Word created successfully", "word": _serialize_word(word, tag_names)}, ensure_ascii=False)


async def update_word(user_id: int, word_id: int, title: str = None,
                      explanation: str = None, notes: str = None,
                      tag_ids: list = None) -> str:
    """Update an existing English word."""
    from main_app.models import EnglishWord, Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        word = await sync_to_async(
            EnglishWord.objects.prefetch_related('tags').get
        )(id=word_id, creator=user)
    except EnglishWord.DoesNotExist:
        return json.dumps({"error": f"Word with id {word_id} not found"})

    if title is not None:
        if title != word.title:
            exists = await sync_to_async(
                EnglishWord.objects.filter(title=title, creator=user).exclude(id=word_id).exists
            )()
            if exists:
                return json.dumps({"error": f"Word '{title}' already exists"})
        word.title = title
    if explanation is not None:
        word.explanation = explanation
    if notes is not None:
        word.notes = notes

    await sync_to_async(word.save)()

    if tag_ids is not None:
        tags = await sync_to_async(list)(WordTag.objects.filter(id__in=tag_ids, creator=user))
        await sync_to_async(word.tags.set)(tags)

    word = await sync_to_async(
        EnglishWord.objects.prefetch_related('tags').get
    )(id=word.id)
    tag_names = await sync_to_async(list)(word.tags.values_list('name', flat=True))
    return json.dumps({"message": "Word updated successfully", "word": _serialize_word(word, tag_names)}, ensure_ascii=False)


async def delete_word(user_id: int, word_id: int) -> str:
    """Delete an English word by ID."""
    from main_app.models import EnglishWord
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        word = await sync_to_async(EnglishWord.objects.get)(id=word_id, creator=user)
        word_title = word.title
        await sync_to_async(word.delete)()
        return json.dumps({"message": f"Word '{word_title}' deleted successfully"})
    except EnglishWord.DoesNotExist:
        return json.dumps({"error": f"Word with id {word_id} not found"})


# ==================== Word Tag Tools ====================

async def list_word_tags(user_id: int, search: str = None, skip: int = 0, limit: int = 50) -> str:
    """List word tags for the user."""
    from main_app.models import Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    queryset = WordTag.objects.filter(creator=user)

    if search:
        queryset = queryset.filter(name__icontains=search)

    total = await sync_to_async(queryset.count)()
    tags = await sync_to_async(list)(queryset.order_by('-created_at')[skip:skip + limit])

    results = []
    for tag in tags:
        word_count = await sync_to_async(tag.english_words.count)()
        results.append(_serialize_word_tag(tag, word_count))

    return json.dumps({"tags": results, "total": total}, ensure_ascii=False)


async def get_word_tag(user_id: int, tag_id: int) -> str:
    """Get a specific word tag by ID."""
    from main_app.models import Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        tag = await sync_to_async(WordTag.objects.get)(id=tag_id, creator=user)
        word_count = await sync_to_async(tag.english_words.count)()
        return json.dumps(_serialize_word_tag(tag, word_count), ensure_ascii=False)
    except WordTag.DoesNotExist:
        return json.dumps({"error": f"Word tag with id {tag_id} not found"})


async def create_word_tag(user_id: int, name: str) -> str:
    """Create a new word tag."""
    from main_app.models import Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)

    exists = await sync_to_async(WordTag.objects.filter(name=name, creator=user).exists)()
    if exists:
        return json.dumps({"error": f"Word tag '{name}' already exists"})

    tag = await sync_to_async(WordTag.objects.create)(name=name, creator=user)
    return json.dumps({"message": f"Word tag '{name}' created successfully", "tag": _serialize_word_tag(tag)}, ensure_ascii=False)


async def update_word_tag(user_id: int, tag_id: int, name: str) -> str:
    """Update a word tag's name."""
    from main_app.models import Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        tag = await sync_to_async(WordTag.objects.get)(id=tag_id, creator=user)
    except WordTag.DoesNotExist:
        return json.dumps({"error": f"Word tag with id {tag_id} not found"})

    if name != tag.name:
        exists = await sync_to_async(WordTag.objects.filter(name=name, creator=user).exclude(id=tag_id).exists)()
        if exists:
            return json.dumps({"error": f"Word tag '{name}' already exists"})

    tag.name = name
    await sync_to_async(tag.save)()
    word_count = await sync_to_async(tag.english_words.count)()
    return json.dumps({"message": f"Word tag updated to '{name}'", "tag": _serialize_word_tag(tag, word_count)}, ensure_ascii=False)


async def delete_word_tag(user_id: int, tag_id: int) -> str:
    """Delete a word tag by ID."""
    from main_app.models import Tag as WordTag
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = await sync_to_async(User.objects.get)(id=user_id)
    try:
        tag = await sync_to_async(WordTag.objects.get)(id=tag_id, creator=user)
        tag_name = tag.name
        await sync_to_async(tag.delete)()
        return json.dumps({"message": f"Word tag '{tag_name}' deleted successfully"})
    except WordTag.DoesNotExist:
        return json.dumps({"error": f"Word tag with id {tag_id} not found"})
