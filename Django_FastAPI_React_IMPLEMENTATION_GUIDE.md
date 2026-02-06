# Full-Stack Implementation Guide: Django + FastAPI + React

A comprehensive reference for building the Goals & Vocabulary Management System — covering the Django + FastAPI backend and the React frontend. Based on real patterns and lessons learned from this project.

---

## Table of Contents

- [Part 1: Architecture Overview](#part-1-architecture-overview)
- [Part 2: Backend — Django + FastAPI](#part-2-backend--django--fastapi)
  - [Implementation Order](#backend-implementation-order)
  - [The Async Pattern — Three Rules](#the-async-pattern--three-rules)
  - [Complete Backend Pattern Examples](#complete-backend-pattern-examples)
  - [Anti-patterns to Avoid](#anti-patterns-to-avoid)
- [Part 3: Frontend — React + TypeScript](#part-3-frontend--react--typescript)
  - [Phase 1 — Project Scaffolding](#phase-1--project-scaffolding)
  - [Phase 2 — Type Definitions](#phase-2--type-definitions-types)
  - [Phase 3 — API Service Layer](#phase-3--api-service-layer-services)
  - [Phase 4 — Auth Context](#phase-4--auth-context-contexts)
  - [Phase 5 — Routing and Layout](#phase-5--routing-and-layout-apptsx-layouts)
  - [Phase 6 — Reusable Components](#phase-6--reusable-components-components)
  - [Phase 7 — Page Components](#phase-7--page-components-pages)
  - [Phase 8 — Polish and Edge Cases](#phase-8--polish-and-edge-cases)
- [Part 4: AI Prompt Templates](#part-4-ai-prompt-templates)
- [Part 5: Common Pitfalls & Reminders](#part-5-common-pitfalls--reminders)
- [Part 6: Quick Reference — Full Project File Structure](#part-6-quick-reference--full-project-file-structure)

---

## Part 1: Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite + TS)                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────┐  │
│  │  Pages   │ │Components│ │  Services  │ │  AuthContext      │  │
│  │ (views)  │ │ (UI)     │ │  (Axios)   │ │  (JWT tokens)    │  │
│  └────┬─────┘ └──────────┘ └─────┬──────┘ └──────────────────┘  │
│       │                          │                               │
│       └──────────────────────────┘                               │
│                    HTTP / JSON                                   │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI (async)                               │
│  ┌───────────┐ ┌──────────┐ ┌────────────────┐                  │
│  │ Endpoints │ │ Pydantic │ │ JWT Auth       │                  │
│  │ (async)   │ │ Models   │ │ (Depends)      │                  │
│  └─────┬─────┘ └──────────┘ └────────────────┘                  │
│        │                                                         │
│  ┌─────▼─────────────────────────────────────┐                   │
│  │         sync_to_async bridge               │                   │
│  └─────┬─────────────────────────────────────┘                   │
│        │                                                         │
│  ┌─────▼─────────────────────────────────────┐                   │
│  │      Sync Helper Functions                │                   │
│  │  (encapsulate all ORM operations)         │                   │
│  └─────┬─────────────────────────────────────┘                   │
│        │                                                         │
├────────▼─────────────────────────────────────────────────────────┤
│                Django ORM (sync)                                 │
│  ┌──────────┐ ┌───────────┐ ┌────────────────┐                  │
│  │  Models  │ │ Managers  │ │  Serializers   │                  │
│  └──────────┘ └───────────┘ └────────────────┘                  │
│                                                                  │
│                MySQL Database                                    │
└──────────────────────────────────────────────────────────────────┘
```

**Key principle:** FastAPI runs in an async event loop. Django ORM is synchronous. Every ORM call that hits the database must go through `sync_to_async`. The React frontend communicates with FastAPI via JSON over HTTP, using JWT tokens for authentication.

---

## Part 2: Backend — Django + FastAPI

### Backend Implementation Order

#### Phase 1 — Django Foundation

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

**Example prompt for AI:**

> "Create Django models for:
> - User (extend AbstractUser with position CharField, age PositiveIntegerField)
> - Goal (title, description, notes, status [choices], priority [choices], urgency, creator FK, tags M2M)
> - Task (name, description, goal FK nullable, creator FK, tags M2M, same status/priority/urgency choices)
> - EnglishWord (title, explanation, notes, creator FK, tags M2M)
> - EnglishWordMedia (word FK, file FileField with extension validation)
>
> Each domain has its own Tag model with `unique_together = ['name', 'creator']`.
> Use `related_name` to avoid clashes (e.g. `'goal_app_tags'`, `'main_app_tags'`)."

**Key considerations:**

- Custom User model must be set **before first migration**: `AUTH_USER_MODEL = 'core.User'`
- Use `settings.AUTH_USER_MODEL` for FK references, not `User` directly
- Set unique `related_name` for FK/M2M to avoid reverse accessor clashes between apps
- Add `blank=True, null=True` for optional fields at model level
- Add `allow_blank=True` for optional CharFields at **serializer** level (DRF is stricter than Django)

#### Phase 2 — FastAPI Layer

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

**Critical: Django must be initialized before FastAPI imports models:**

```python
# api/main.py — MUST be at the top, before any model imports
import os, django, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root_directory.settings')
django.setup()  # <-- MUST happen before importing any Django models

from fastapi import FastAPI
# ... now safe to import routes that use Django models
```

---

### The Async Pattern — Three Rules

**This is the most important technical concept in the backend.** FastAPI runs async, Django ORM is sync. You must bridge this correctly.

#### Rule 1: Create sync functions that encapsulate COMPLETE ORM operations

Every database operation should be wrapped in a regular Python function:

```python
def sync_get_items(queryset, skip: int, limit: int):
    """ONE sync function = ONE complete database operation"""
    total = queryset.count()
    items = list(queryset.order_by('-created_time')[skip:skip + limit])
    return items, total
```

**Why?** This keeps all ORM logic in one place, makes it testable, and ensures Django's ORM thread-local connections are used correctly.

#### Rule 2: Use `sync_to_async` to call sync functions from async context

```python
from asgiref.sync import sync_to_async

async def async_get_items(queryset, skip, limit):
    return await sync_to_async(sync_get_items)(queryset, skip, limit)
```

**Why?** `sync_to_async` runs the function in a thread pool, keeping the async event loop unblocked.

#### Rule 3: NEVER chain QuerySet evaluation across async boundaries

```python
# OK — Lazy QuerySet building (no DB hit):
queryset = Item.objects.filter(creator=user)
queryset = queryset.filter(status=status)
queryset = queryset.select_related('creator')

# MUST WRAP — QuerySet evaluation (DB hit):
total = await sync_to_async(queryset.count)()
items = await sync_to_async(list)(queryset[:limit])
```

#### What is OK (Lazy QuerySet Building)

```python
# OK: Building QuerySets is lazy (no DB hit), so no async wrapper needed
queryset = Item.objects.filter(creator=user)
if status:
    queryset = queryset.filter(status=status)
if tag_id:
    queryset = queryset.filter(tags__id=tag_id)
queryset = queryset.select_related('creator').prefetch_related('tags')

# Only EVALUATE when you call count(), list(), get(), save(), delete() — wrap THOSE
```

#### TYPE_CHECKING Pattern for Django Models

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User  # IDE type hints
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()  # Runtime: gets actual custom User model
```

---

### Complete Backend Pattern Examples

#### Example 1: List Endpoint with Filters (from `goals.py`)

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

#### Example 2: Create Endpoint with M2M (from `words.py`)

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

#### Example 3: File Upload (from `words.py`)

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

#### Example 4: User Authentication (from `auth.py`)

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

async def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="User inactive")
    return current_user

# All endpoints use:
@router.get("/")
async def list_items(current_user: User = Depends(get_current_active_user)):
    # current_user is guaranteed to be authenticated and active
    queryset = Item.objects.filter(creator=current_user)
    ...
```

---

### Anti-patterns to Avoid

#### ❌ Evaluating QuerySet directly in async context

```python
# WRONG
async def list_items():
    queryset = Item.objects.filter(creator=user)
    count = queryset.count()     # SYNC call in ASYNC context!
    items = list(queryset[:10])  # SYNC call in ASYNC context!
```

#### ❌ Accessing related fields without wrapper

```python
# WRONG
async def to_response(item):
    tags = list(item.tags.all())  # SYNC ORM call!
    goal_title = item.goal.title  # SYNC FK access (if not prefetched)!
```

#### ❌ Importing models at module level in api/ files

```python
# RISKY — may fail if Django hasn't finished setup
from goal_app.models import Goal  # at top of file

# SAFE — import inside function
def sync_get_goals():
    from goal_app.models import Goal  # imported when called
    return list(Goal.objects.all())
```

#### ❌ Mixing sync and async in one logical operation without grouping

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

## Part 3: Frontend — React + TypeScript

**Prerequisite:** Backend API and request/response contracts are ready.

### Phase 1 — Project Scaffolding

**Order:**

1. Initialize project: `npm create vite@latest -- --template react-ts`
2. Install core dependencies: `react-router-dom`, `axios`, `tailwindcss`, `clsx`, `lucide-react`
3. Configure Tailwind CSS (`tailwind.config.js`, `postcss.config.js`, `index.css`)
4. Configure Vite dev server proxy and port (`vite.config.ts`)
5. Configure TypeScript (`tsconfig.json`, `tsconfig.node.json`)

**Example prompt for AI:**

> "Initialize a Vite + React + TypeScript project. Install react-router-dom, axios, tailwindcss, clsx, lucide-react. Configure Tailwind with a dark theme color palette (provide palette). Set dev server port to 3000 with API proxy to http://localhost:8001."

**Example `vite.config.ts`:**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
})
```

---

### Phase 2 — Type Definitions (`types/`)

**This is foundational** — everything else depends on correct types. `types/index.ts` is the single source of truth.

**Order:**

1. Define all TypeScript interfaces matching backend API response/request contracts
2. Group by domain: Auth, Goal, Task, Word, Tag
3. Include list response wrappers and pagination params

**Example prompt for AI:**

> "Here are the backend API response schemas (paste Pydantic models or Swagger JSON). Create TypeScript interfaces in `src/types/index.ts` that match these contracts exactly. Group by domain: Auth, Goal, Task, Word, Tag. Include list response wrappers and pagination params."

**Key considerations:**

- Backend field names must match **exactly** (e.g. `created_time` vs `created_at`, `creator_id` vs `user_id`)
- Nullable fields → `string | null`, optional request fields → `field?: type`
- Enum values must match backend choices (e.g. `'not_started' | 'in_progress' | 'completed'`)

**Real example from this project:**

```typescript
// ==================== Goal Types ====================
export interface Goal {
  id: number;
  title: string;
  description: string | null;    // nullable → string | null
  notes: string | null;
  status: 'not_started' | 'in_progress' | 'completed' | 'on_hold';  // match backend choices
  priority: 'low' | 'medium' | 'high';
  urgency: 'low' | 'medium' | 'high';
  creator_id: number;
  created_time: string;           // backend uses created_time, not created_at
  tags: string[];                 // API returns tag names, not IDs
}

export interface GoalCreate {
  title: string;
  description?: string;           // optional in creation
  notes?: string;
  status?: string;
  priority?: string;
  urgency?: string;
  tags?: number[];                // create/update uses tag IDs, not names
}

export interface GoalListResponse {
  goals: Goal[];
  total: number;
  page: number;
  size: number;
}

// Reusable pagination params
export interface PaginationParams {
  skip?: number;
  limit?: number;
}
```

---

### Phase 3 — API Service Layer (`services/`)

**Order:**

1. `api.ts` — Axios instance, token management, request/response interceptors
2. `auth.ts` — login, register, logout, getCurrentUser, refreshToken
3. Business domain services: `words.ts`, `goals.ts`, `tasks.ts`, `tags.ts`
4. `index.ts` — barrel export

**Example prompt for AI:**

> "Create an Axios service layer.
> - `api.ts`: base URL http://localhost:8001, auto-attach Bearer token from localStorage, implement 401 interceptor with refresh token queue (reference backend's POST /api/auth/refresh, request body: {refresh_token}).
> - Login endpoint uses `application/x-www-form-urlencoded` (OAuth2 form).
> - Create service files for each domain with CRUD methods matching these endpoints: [list endpoints]."

**Critical details for `api.ts`:**

```typescript
// Token refresh interceptor — must queue concurrent 401 requests
let isRefreshing = false;
let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // CRITICAL: Skip token refresh for auth endpoints to avoid infinite loops
    const isAuthEndpoint = originalRequest.url?.includes('/api/auth/token') ||
                           originalRequest.url?.includes('/api/auth/register') ||
                           originalRequest.url?.includes('/api/auth/refresh');

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      // ... refresh logic with queue
    }
    return Promise.reject(error);
  }
);
```

**Critical: Login uses URLSearchParams, NOT JSON:**

```typescript
// CORRECT — FastAPI's OAuth2PasswordRequestForm expects form data
const formData = new URLSearchParams();
formData.append('username', username);
formData.append('password', password);

const response = await api.post<Token>('/api/auth/token', formData, {
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
});

// WRONG — This will fail with FastAPI's OAuth2PasswordRequestForm
// const response = await api.post('/api/auth/token', { username, password });
```

**Critical: File uploads need multipart/form-data:**

```typescript
uploadMedia: async (wordId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post(`/api/words/${wordId}/media`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
},
```

**Domain service pattern (consistent for all resources):**

```typescript
export const goalsService = {
  getAll: async (params?: PaginationParams & {
    status?: string;
    priority?: string;
    tag_id?: number;
  }): Promise<GoalListResponse> => {
    const response = await api.get<GoalListResponse>('/api/goals/', { params });
    return response.data;
  },

  getById: async (id: number): Promise<Goal> => {
    const response = await api.get<Goal>(`/api/goals/${id}`);
    return response.data;
  },

  create: async (data: GoalCreate): Promise<Goal> => {
    const response = await api.post<Goal>('/api/goals/', data);
    return response.data;
  },

  update: async (id: number, data: GoalUpdate): Promise<Goal> => {
    const response = await api.put<Goal>(`/api/goals/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/api/goals/${id}`);
  },
};
```

---

### Phase 4 — Auth Context (`contexts/`)

**Order:**

1. `AuthContext.tsx` — AuthProvider wrapping the entire app

**Example prompt for AI:**

> "Create AuthContext with: user state, isAuthenticated, isLoading, login/register/logout/refreshUser methods. On mount, check localStorage for tokens and call GET /api/auth/me to restore session. Wrap login to call POST /api/auth/token then GET /api/auth/me. Wrap logout to call POST /api/auth/logout and clear tokens."

**Key considerations:**

- `isLoading` state is **critical** — prevents flash of login page on page refresh
- `useCallback` for all context methods to prevent unnecessary re-renders
- On mount: check if tokens exist in localStorage → if yes, call `/api/auth/me` to validate

**Pattern:**

```typescript
const AuthProvider: React.FC = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);  // starts true!

  useEffect(() => {
    const initAuth = async () => {
      const tokens = tokenManager.getTokens();
      if (tokens) {
        try {
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
        } catch {
          tokenManager.clearTokens(); // token invalid, clear it
        }
      }
      setIsLoading(false);  // only set false AFTER check completes
    };
    initAuth();
  }, []);

  // ... login, logout, register (all wrapped in useCallback)
};
```

---

### Phase 5 — Routing and Layout (`App.tsx`, `layouts/`)

**Order:**

1. `main.tsx` — `BrowserRouter` > `AuthProvider` > `App`
2. `App.tsx` — Route definitions with ProtectedRoute/PublicRoute wrappers
3. `DashboardLayout.tsx` — Sidebar nav + header + `<Outlet />`

**Example prompt for AI:**

> "Create routing: public routes (login, register) redirect to dashboard if authenticated. Protected routes redirect to login if not authenticated. Dashboard layout with left sidebar navigation (sections: Vocabulary [Words, Word Tags], Goals & Tasks [Goals, Tasks, Goal Tags]), top header with user dropdown menu and logout. Use React Router v6 nested routes with Outlet."

**Key considerations:**

- Use `<Navigate replace />` to avoid back-button loops
- `ProtectedRoute` must wait for `isLoading` to be false before redirecting
- Add React Router v7 future flags to suppress warnings:

```tsx
<BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
```

**Nesting structure:**

```tsx
<Routes>
  <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
  <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />

  <Route path="/dashboard" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
    <Route index element={<Navigate to="words" replace />} />
    <Route path="words" element={<WordsPage />} />
    <Route path="words/:id" element={<WordDetailPage />} />
    <Route path="goals" element={<GoalsPage />} />
    <Route path="tasks" element={<TasksPage />} />
    {/* ... more routes */}
  </Route>

  <Route path="*" element={<Navigate to="/dashboard/words" replace />} />
</Routes>
```

---

### Phase 6 — Reusable Components (`components/`)

**Order:**

1. `Modal.tsx` — Generic modal (escape key, backdrop, body scroll lock, multiple sizes)
2. `ConfirmDialog.tsx` — Extends Modal for delete confirmations
3. `EmptyState.tsx` — Empty list placeholder with optional CTA button
4. `LoadingSpinner.tsx` — Loading indicator
5. `Pagination.tsx` — Reusable page navigation (first/prev/pages/next/last)

**Example prompt for AI:**

> "Create these reusable components: Modal (with sizes sm/md/lg/xl/2xl/4xl, escape to close, backdrop, body scroll lock), ConfirmDialog (danger action modal with cancel/confirm buttons), EmptyState (icon + title + description + optional CTA), LoadingSpinner, Pagination (first/prev/page numbers with ellipsis/next/last, showing 'X to Y of Z results')."

---

### Phase 7 — Page Components (`pages/`)

**Recommended implementation order:**

1. `LoginPage.tsx` + `RegisterPage.tsx` — Auth flow first (test end-to-end)
2. `WordsPage.tsx` — First list page with CRUD modal, search, tag filter, pagination
3. `WordDetailPage.tsx` — Detail page with media upload/preview/download/delete
4. `GoalsPage.tsx` — List with status/priority/tag filters + CRUD
5. `TasksPage.tsx` — List with status/priority/goal/tag filters + CRUD
6. `WordTagsPage.tsx` + `GoalTagsPage.tsx` — Tag CRUD

**Example prompt for a list page:**

> "Create WordsPage with:
> 1. State: items, tags, isLoading, search, tagFilter, pagination (currentPage, totalItems, totalPages), selectedItem, isFormOpen, isDeleteOpen
> 2. Fetch data with useCallback, pass search/tag_id/skip/limit params
> 3. Debounced search (300ms) resets to page 1
> 4. Tag filter dropdown resets to page 1
> 5. CRUD via Modal form with tag toggle buttons
> 6. Delete via ConfirmDialog
> 7. Pagination component at bottom
> Use the service layer, NOT direct axios calls."

**Key state management pattern for list pages:**

```tsx
// 1. Fetch function — wrapped in useCallback with all filter dependencies
const fetchWords = useCallback(async (page: number = currentPage) => {
  setIsLoading(true);
  try {
    const skip = (page - 1) * PAGE_SIZE;
    const response = await wordsService.getAll({
      search: search || undefined,
      tag_id: tagFilter ? parseInt(tagFilter) : undefined,
      skip,
      limit: PAGE_SIZE,
    });
    setWords(response.words);
    setTotalItems(response.total);
    setTotalPages(Math.ceil(response.total / PAGE_SIZE));
  } catch (err) { console.error(err); }
  finally { setIsLoading(false); }
}, [search, tagFilter, currentPage]);

// 2. Separate useEffects for different triggers
useEffect(() => { fetchWords(currentPage); }, [currentPage, fetchWords]);

// 3. Debounced search — resets to page 1
useEffect(() => {
  const timer = setTimeout(() => { setCurrentPage(1); fetchWords(1); }, 300);
  return () => clearTimeout(timer);
}, [search]);

// 4. Filter change — resets to page 1
useEffect(() => { setCurrentPage(1); fetchWords(1); }, [tagFilter]);
```

**Tag ID vs Tag Name — the common gotcha:**

```tsx
// API RETURNS tag names (strings) in list responses
// word.tags = ["vocabulary", "grammar"]

// API EXPECTS tag IDs (numbers) in create/update requests
// { tags: [1, 5, 12] }

// Converting names to IDs for the edit form:
const openEditForm = (word: Word) => {
  const tagIds = tags.filter(t => word.tags.includes(t.name)).map(t => t.id);
  setFormData({ ...word, tags: tagIds });
};
```

**Action buttons inside clickable cards — use stopPropagation:**

```tsx
<div className="card cursor-pointer" onClick={() => viewDetail(item)}>
  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
    <button onClick={() => openEditForm(item)}>Edit</button>
    <button onClick={() => openDeleteDialog(item)}>Delete</button>
  </div>
</div>
```

---

### Phase 8 — Polish and Edge Cases

- CORS configuration on backend if not using Vite proxy
- Error messages for login failures (401 → "Username or password is incorrect")
- Upload success/error feedback with auto-dismiss (setTimeout + state)
- File download via Blob (not just `window.open`) for proper filename preservation
- Responsive design: mobile sidebar toggle, responsive grid layouts

**File download pattern:**

```typescript
const handleDownload = async (media: MediaFileInfo) => {
  try {
    const response = await fetch(fullUrl);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = media.filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch {
    window.open(fullUrl, '_blank'); // fallback
  }
};
```

---

## Part 4: AI Prompt Templates

### Template A: Adding a New CRUD Resource (Backend)

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

### Template B: Adding a New CRUD Resource (Frontend)

> "Add `[ResourceName]` to the frontend:
> 1. Add TypeScript types to `types/index.ts` matching these Pydantic response models: [paste]
> 2. Add service in `services/[resource].ts` with getAll(params), getById(id), create(data), update(id, data), delete(id)
> 3. Add list page `pages/[Resource]Page.tsx` with: search, tag filter dropdown, pagination, CRUD via Modal, delete via ConfirmDialog
> 4. Add route in App.tsx under dashboard
> 5. Add nav item in DashboardLayout.tsx
> Follow the same pattern as `WordsPage.tsx`."

### Template C: Adding a Filter

**Backend:**

> "Add `[field]: Optional[[type]] = Query(None)` to `GET /api/[resource]/`.
> Filter: `queryset = queryset.filter([field]=[value])`.
> This is lazy QuerySet building — no sync_to_async needed for the filter itself."

**Frontend:**

> "Add tag filter dropdown to `[Resource]Page`. State: `tagFilter` string. Fetch tags from `tagsService.getAll({tag_type: '[type]'})`. Pass `tag_id: tagFilter ? parseInt(tagFilter) : undefined` to service call. Reset to page 1 when tagFilter changes."

### Template D: Adding Media/File Upload (Backend)

> "Add file upload endpoint to `/api/[resource]/{id}/media`.
> - Create `sync_create_media_file(parent, filename, content)` that uses Django's `ContentFile`
> - Endpoint reads file with `await file.read()` (async)
> - Saves via `await sync_to_async(sync_create_media_file)(...)`
> - Validate file extension against allowed list
> Reference: follow `api/words.py` upload pattern."

### Template E: Adding a Detail Page (Frontend)

> "Create `[Resource]DetailPage.tsx` for `GET /api/[resource]/{id}`. Display all fields prominently. Include:
> - Edit button → opens Modal with form
> - Delete button → ConfirmDialog
> - Back button → navigate to list
> - If media upload is supported: file upload section with hidden file input, upload button, success/error messages, media grid with preview/download/delete overlay buttons
> - Use Blob download for proper filenames
> Follow the same pattern as `WordDetailPage.tsx`."

### Template F: Adding Pagination

**Backend:**

> "The endpoint `GET /api/[resource]/` already accepts `skip` and `limit` params and returns `total` count. No backend changes needed."

**Frontend:**

> "Add pagination to `[Resource]Page`:
> 1. Add state: currentPage (1), totalItems (0), totalPages (1)
> 2. Calculate skip = (currentPage - 1) * PAGE_SIZE in fetch function
> 3. Set totalPages = Math.ceil(response.total / PAGE_SIZE) after fetch
> 4. Add `<Pagination>` component at bottom of list
> 5. handlePageChange sets currentPage, which triggers fetch via useEffect
> 6. Reset to page 1 when search/filters change"

---

## Part 5: Common Pitfalls & Reminders

### Backend Pitfalls

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
| `sync_to_async` thread safety | Multiple ORM calls in separate dispatches | Each sync function should be self-contained; import models **inside** functions |

### Frontend Pitfalls

| Issue | Solution |
|-------|----------|
| Token refresh infinite loop | Skip refresh interceptor for `/api/auth/token`, `/api/auth/register`, `/api/auth/refresh` |
| Flash of login page on refresh | Use `isLoading` state in AuthContext; show spinner until token validation completes |
| OAuth2 login format | Use `URLSearchParams` with `Content-Type: application/x-www-form-urlencoded`, NOT JSON |
| CORS errors | Add frontend origin to backend `allow_origins` in FastAPI CORSMiddleware |
| Tag ID vs Name mismatch | API returns tag **names** (strings) in lists, but create/update expect tag **IDs** (numbers). Convert via tag list lookup |
| Stale closures in useCallback | Include ALL dependencies (search, filters, currentPage) in dependency array |
| useEffect firing loops | Use separate effects for: mount, pagination, debounced search, filter changes |
| Download not working | Use `fetch` → `Blob` → `createObjectURL` → programmatic `<a>` click, NOT just `window.open` |
| `tsconfig.json` errors | If using project references, set `composite: true`, `declaration: true` in referenced tsconfig |

### Checklist When Writing Requirements for AI

1. **Always provide the backend API contract** — Pydantic models or Swagger/OpenAPI spec
2. **Specify exact field names** — `created_time` vs `created_at` matters
3. **Specify enum values** — `'not_started'` vs `'notStarted'` must match backend
4. **Mention the async pattern** — "Use sync_to_async wrapper pattern" for any new backend endpoint
5. **Specify which tag_type** — Your system has two separate Tag models (`goals` and `words`)
6. **Reference existing files** — "Follow the same pattern as `WordsPage.tsx`" saves extensive explanation
7. **Mention special API formats** — e.g. "Login uses OAuth2 form data, not JSON"
8. **Specify UI style** — "Use the existing Tailwind dark theme and component classes (btn-primary, input, card)"
9. **List the dependencies** — "The page needs to fetch both words and tags on mount"
10. **Describe the expected UX flow** — "After successful creation, close the modal and refresh the list"

---

## Part 6: Quick Reference — Full Project File Structure

### Backend (`Goals`)

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
└── requirements.txt
```

### Frontend (`Goals_Front_End`)

```
src/
├── types/index.ts           ← All TypeScript interfaces
├── services/
│   ├── api.ts               ← Axios instance + interceptors
│   ├── auth.ts              ← Auth API calls
│   ├── words.ts             ← Words CRUD
│   ├── goals.ts             ← Goals CRUD
│   ├── tasks.ts             ← Tasks CRUD
│   ├── tags.ts              ← Tags CRUD
│   └── index.ts             ← Barrel export
├── contexts/
│   └── AuthContext.tsx       ← Auth state management
├── layouts/
│   └── DashboardLayout.tsx   ← Sidebar + header + Outlet
├── components/
│   ├── Modal.tsx             ← Generic modal
│   ├── ConfirmDialog.tsx     ← Delete confirmation
│   ├── EmptyState.tsx        ← Empty list placeholder
│   ├── LoadingSpinner.tsx    ← Loading indicator
│   └── Pagination.tsx        ← Page navigation
├── pages/
│   ├── LoginPage.tsx         ← Login form
│   ├── RegisterPage.tsx      ← Registration form
│   ├── WordsPage.tsx         ← Words list + CRUD
│   ├── WordDetailPage.tsx    ← Word detail + media
│   ├── GoalsPage.tsx         ← Goals list + CRUD
│   ├── TasksPage.tsx         ← Tasks list + CRUD
│   ├── WordTagsPage.tsx      ← Word tags CRUD
│   └── GoalTagsPage.tsx      ← Goal tags CRUD
├── App.tsx                   ← Route definitions
├── main.tsx                  ← Entry point
└── index.css                 ← Global styles + Tailwind
```
