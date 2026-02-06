# Backend Implementation Guide: Django + FastAPI Async Patterns

A comprehensive reference for the Django + FastAPI backend architecture, focusing on the critical async/sync bridging pattern. For the companion frontend guide, see `Goals_Front_End/IMPLEMENTATION_GUIDE.md`.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Implementation Order](#implementation-order)
- [The Async Pattern — Three Rules](#the-async-pattern--three-rules)
- [Complete Pattern Examples from This Codebase](#complete-pattern-examples-from-this-codebase)
- [Anti-patterns to Avoid](#anti-patterns-to-avoid)
- [AI Prompt Templates](#ai-prompt-templates)
- [Common Pitfalls](#common-pitfalls)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   FastAPI (async)                │
│  ┌───────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Endpoints │ │ Pydantic │ │ JWT Auth       │  │
│  │ (async)   │ │ Models   │ │ (Depends)      │  │
│  └─────┬─────┘ └──────────┘ └────────────────┘  │
│        │                                         │
│  ┌─────▼─────────────────────────────────────┐   │
│  │         sync_to_async bridge               │   │
│  └─────┬─────────────────────────────────────┘   │
│        │                                         │
│  ┌─────▼─────────────────────────────────────┐   │
│  │      Sync Helper Functions                │   │
│  │  (encapsulate all ORM operations)         │   │
│  └─────┬─────────────────────────────────────┘   │
│        │                                         │
├────────▼─────────────────────────────────────────┤
│                Django ORM (sync)                 │
│  ┌──────────┐ ┌───────────┐ ┌────────────────┐  │
│  │  Models  │ │ Managers  │ │  Serializers   │  │
│  └──────────┘ └───────────┘ └────────────────┘  │
│                                                  │
│                MySQL Database                    │
└──────────────────────────────────────────────────┘
```

**Key principle:** FastAPI runs in an async event loop. Django ORM is synchronous. Every ORM call that hits the database must go through `sync_to_async`.

---

## Implementation Order

### Phase 1 — Django Foundation

1. **Create Django project and apps:**
   ```bash
   django-admin startproject root_directory .
   python manage.py startapp core
   python manage.py startapp goal_app
   python manage.py startapp main_app
   ```

2. **Define models** (the data layer comes first):
   - `core/models.py` — Custom User (extends `AbstractUser`)
   - `goal_app/models.py` — Goal, Task, Tag (for goals/tasks), Attachments
   - `main_app/models.py` — EnglishWord, Tag (for words), EnglishWordMedia

3. **Create serializers** (`core/serializers.py`):
   - `UserCreateSerializer` — handles password hashing
   - `UserSerializer` — general user data

4. **Configure settings** (`root_directory/settings.py`):
   - `AUTH_USER_MODEL = 'core.User'` (BEFORE first migration!)
   - Database, CORS, media files, JWT config, cache, logging

5. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

### Phase 2 — FastAPI Layer

1. **`api/main.py`** — App setup (this is the entry point):
   - Django environment initialization (MUST be first)
   - FastAPI instance with CORS middleware
   - Route mounting for all modules
   - Static file serving for media

2. **`api/auth.py`** — Authentication (everything depends on this):
   - Pydantic models for requests/responses
   - JWT token creation and verification
   - Token blacklisting (via Django cache)
   - Dependency injection: `get_current_user` → `get_current_active_user`
   - Endpoints: register, login, refresh, logout, get-me

3. **`api/goals.py`** — First business resource:
   - Sync helper functions
   - Async wrappers
   - CRUD endpoints

4. **`api/tasks.py`** — Tasks (depends on Goals for FK):
   - Same pattern as goals
   - Additional: Goal FK validation

5. **`api/words.py`** — Words + media:
   - Same CRUD pattern
   - Additional: file upload/delete endpoints

6. **`api/tags.py`** — Tags (unified for both domains):
   - Handles two separate Tag models via `tag_type` parameter

---

## The Async Pattern — Three Rules

### Rule 1: Create sync functions that encapsulate COMPLETE ORM operations

Every database operation should be wrapped in a regular Python function:

```python
def sync_get_items(queryset, skip: int, limit: int):
    """ONE sync function = ONE complete database operation"""
    total = queryset.count()
    items = list(queryset.order_by('-created_time')[skip:skip + limit])
    return items, total
```

**Why?** This keeps all ORM logic in one place, makes it testable, and ensures Django's ORM thread-local connections are used correctly.

### Rule 2: Use `sync_to_async` to call sync functions from async context

```python
from asgiref.sync import sync_to_async

async def async_get_items(queryset, skip, limit):
    return await sync_to_async(sync_get_items)(queryset, skip, limit)
```

**Why?** `sync_to_async` runs the function in a thread pool, keeping the async event loop unblocked.

### Rule 3: NEVER chain QuerySet evaluation across async boundaries

```python
# OK — Lazy QuerySet building (no DB hit):
queryset = Item.objects.filter(creator=user)
queryset = queryset.filter(status=status)
queryset = queryset.select_related('creator')

# MUST WRAP — QuerySet evaluation (DB hit):
total = await sync_to_async(queryset.count)()
items = await sync_to_async(list)(queryset[:limit])
```

---

## Complete Pattern Examples from This Codebase

### Example 1: List Endpoint with Filters (from `goals.py`)

```python
# ===== Sync helpers =====

def sync_get_goals(queryset, skip, limit):
    """All ORM evaluation in one sync function"""
    queryset = queryset.select_related('creator').prefetch_related('tags')
    total = queryset.count()
    goals = list(queryset.order_by('-created_time')[skip:skip + limit])
    return goals, total

# ===== Async wrapper =====

async def async_get_goals(queryset, skip, limit):
    return await sync_to_async(sync_get_goals)(queryset, skip, limit)

# ===== Response converter (accessing related fields) =====

async def async_goal_to_response(goal) -> GoalResponse:
    # M2M access MUST be wrapped
    tags_queryset = goal.tags.all()
    tag_names = await sync_to_async(list)(tags_queryset.values_list('name', flat=True))

    return GoalResponse(
        id=goal.id,
        title=goal.title,
        tags=tag_names,
        # ... other fields
    )

# ===== Endpoint =====

@router.get("/", response_model=GoalListResponse)
async def list_goals(
    skip: int = Query(0),
    limit: int = Query(100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    tag_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user)
):
    from goal_app.models import Goal

    # Lazy filter building — no DB hit, no wrapper needed
    queryset = Goal.objects.filter(creator=current_user)
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)
    if tag_id:
        queryset = queryset.filter(tags__id=tag_id)

    # Evaluate — through async wrapper
    goals, total = await async_get_goals(queryset, skip, limit)

    # Convert — each conversion accesses M2M (needs wrapper)
    responses = []
    for goal in goals:
        responses.append(await async_goal_to_response(goal))

    return GoalListResponse(goals=responses, total=total, page=skip//limit+1, size=len(responses))
```

### Example 2: Create Endpoint with M2M (from `words.py`)

```python
# ===== Sync helper for existence check =====

def sync_check_title_exists(title, creator, exclude_id=None):
    from main_app.models import EnglishWord
    qs = EnglishWord.objects.filter(title=title, creator=creator)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs.exists()

# ===== Endpoint =====

@router.post("/", response_model=WordResponse, status_code=201)
async def create_word(
    word_data: WordCreate,
    current_user: User = Depends(get_current_active_user)
):
    from main_app.models import EnglishWord, Tag as WordTag

    # Check uniqueness — wraps sync helper
    title_exists = await sync_to_async(sync_check_title_exists)(
        word_data.title, current_user
    )
    if title_exists:
        raise HTTPException(status_code=400, detail="Word already exists")

    # Create — wraps ORM create
    word = await sync_to_async(EnglishWord.objects.create)(
        title=word_data.title,
        explanation=word_data.explanation,
        notes=word_data.notes,
        creator=current_user
    )

    # Set M2M tags — wraps ORM filter + set
    if word_data.tags:
        tags = await sync_to_async(list)(
            WordTag.objects.filter(id__in=word_data.tags, creator=current_user)
        )
        await sync_to_async(word.tags.set)(tags)

    # Re-fetch with related — wraps ORM get with prefetch
    word = await sync_to_async(
        EnglishWord.objects.select_related('creator')
        .prefetch_related('tags', 'media_files').get
    )(id=word.id)

    return await async_word_to_response(word)
```

### Example 3: File Upload (from `words.py`)

```python
# ===== Sync helper — file I/O is sync in Django =====

def sync_create_media_file(word, filename, file_content):
    from main_app.models import EnglishWordMedia
    from django.core.files.base import ContentFile
    media = EnglishWordMedia(word=word)
    media.file.save(filename, ContentFile(file_content))
    media.save()
    return media

# ===== Endpoint =====

@router.post("/{word_id}/media")
async def upload_media(
    word_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    # Validate word ownership
    word = await sync_to_async(EnglishWord.objects.get)(id=word_id, creator=current_user)

    # Read file content — FastAPI async
    file_content = await file.read()

    # Save file — Django sync, wrapped
    media = await sync_to_async(sync_create_media_file)(word, file.filename, file_content)

    return MediaFileResponse(id=media.id, file_url=media.file.url, uploaded_at=media.uploaded_at)
```

### Example 4: User Authentication (from `auth.py`)

```python
# ===== Sync helpers =====

def sync_authenticate_user(username: str, password: str):
    """Wraps Django's authenticate() — completely sync"""
    from django.contrib.auth import authenticate
    return authenticate(username=username, password=password)

def sync_get_user_by_id(user_id: int):
    """Wraps User.objects.get() — completely sync"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

# ===== Async wrappers =====

async def async_authenticate(username, password):
    return await sync_to_async(sync_authenticate_user)(username=username, password=password)

async def async_get_user(user_id):
    return await sync_to_async(sync_get_user_by_id)(user_id)

# ===== Dependency injection (used by ALL endpoints) =====

async def get_current_user(token = Depends(security)) -> User:
    payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("user_id")
    user = await async_get_user(user_id)  # async wrapper for ORM
    if user is None:
        raise HTTPException(status_code=401)
    return user
```

---

## Anti-patterns to Avoid

### ❌ Evaluating QuerySet directly in async context

```python
# WRONG
async def list_items():
    queryset = Item.objects.filter(creator=user)
    count = queryset.count()     # SYNC call in ASYNC context!
    items = list(queryset[:10])  # SYNC call in ASYNC context!
```

### ❌ Accessing related fields without wrapper

```python
# WRONG
async def to_response(item):
    tags = list(item.tags.all())  # SYNC ORM call!
    goal_title = item.goal.title  # SYNC FK access (if not prefetched)!
```

### ❌ Importing models at module level in api/ files

```python
# RISKY — may fail if Django hasn't finished setup
from goal_app.models import Goal  # at top of file

# SAFE — import inside function
def sync_get_goals():
    from goal_app.models import Goal  # imported when called
    return list(Goal.objects.all())
```

### ❌ Mixing sync and async in one logical operation without grouping

```python
# FRAGILE — 3 separate thread pool dispatches
async def create_with_tags(data):
    item = await sync_to_async(Item.objects.create)(**data)
    tags = await sync_to_async(list)(Tag.objects.filter(id__in=data['tags']))
    await sync_to_async(item.tags.set)(tags)

# BETTER — one sync function, one dispatch
def sync_create_with_tags(data):
    item = Item.objects.create(**data)
    tags = list(Tag.objects.filter(id__in=data['tags']))
    item.tags.set(tags)
    return item

async def create_with_tags(data):
    return await sync_to_async(sync_create_with_tags)(data)
```

---

## AI Prompt Templates

### New CRUD Resource (Backend)

> "Add a new FastAPI resource `[Name]` in `api/[name].py`.
>
> Django model: [describe fields, types, choices, FKs, M2Ms]
>
> **Follow this pattern:**
> 1. Sync helper functions: `sync_get_[items]`, `sync_check_exists`
> 2. Async wrappers: `async_get_[items]`
> 3. Response converter: `async_[item]_to_response` with `sync_to_async` for M2M access
> 4. Endpoints: GET / (list + pagination + filters), GET /{id}, POST /, PUT /{id}, DELETE /{id}
> 5. All endpoints: `current_user = Depends(get_current_active_user)`, filter by `creator=current_user`
> 6. Lazy QuerySet building → sync_to_async for evaluation
>
> Reference: follow the pattern in `api/goals.py`."

### Adding a Filter (Backend)

> "Add `[field]: Optional[[type]] = Query(None)` to `GET /api/[resource]/`.
> Filter: `queryset = queryset.filter([field]=[value])`.
> This is lazy QuerySet building — no sync_to_async needed for the filter itself."

### Adding Media/File Upload (Backend)

> "Add file upload endpoint to `/api/[resource]/{id}/media`.
> - Create `sync_create_media_file(parent, filename, content)` that uses Django's `ContentFile`
> - Endpoint reads file with `await file.read()` (async)
> - Saves via `await sync_to_async(sync_create_media_file)(...)`
> - Validate file extension against allowed list
> Reference: follow `api/words.py` upload pattern."

---

## Common Pitfalls

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| `SynchronousOnlyOperation` exception | ORM call in async context without wrapper | Wrap in `sync_to_async` |
| MySQL connection drops after idle | Connection pool timeout | Restart FastAPI; set `CONN_MAX_AGE` |
| N+1 query on M2M fields | Missing `prefetch_related` | Add `.prefetch_related('tags')` to QuerySet |
| `AppRegistryNotReady` on import | Model imported before `django.setup()` | Import models inside functions, not at module level |
| DRF serializer rejects blank string | Missing `allow_blank=True` | Add to CharField in serializer (DRF is stricter than model layer) |
| Token refresh fails silently | Blacklisted token not checked | Check `is_token_blacklisted()` in `get_current_user` |
| CORS blocks preflight | Frontend origin not in `allow_origins` | Add exact origin (including port) to `CORSMiddleware` |
| `unique_together` violation on tag create | Same name + creator + type | Check existence before creation with `sync_check_tag_name_exists` |

---

## Quick Reference: File Structure

```
Goals/
├── api/                          ← FastAPI layer
│   ├── main.py                   ← App setup, Django init, CORS, routes
│   ├── auth.py                   ← JWT auth, user management
│   ├── goals.py                  ← Goal CRUD (sync → async → endpoint)
│   ├── tasks.py                  ← Task CRUD
│   ├── words.py                  ← Word CRUD + media upload
│   └── tags.py                   ← Tag CRUD (unified goals + words)
│
├── core/                         ← Django: User model
│   ├── models.py                 ← Custom User (AbstractUser + position, age)
│   └── serializers.py            ← UserCreateSerializer, UserSerializer
│
├── goal_app/                     ← Django: Goals domain
│   └── models.py                 ← Goal, Task, Tag, Attachments
│
├── main_app/                     ← Django: Vocabulary domain
│   ├── models.py                 ← EnglishWord, Tag, EnglishWordMedia
│   └── signals.py                ← Auto-delete media files
│
├── root_directory/               ← Django project config
│   └── settings.py               ← DB, JWT, CORS, media, cache, logging
│
├── manage.py
├── requirements.txt
└── IMPLEMENTATION_GUIDE.md       ← This file
```
