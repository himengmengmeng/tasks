<p align="center">
  <a href="README.md">English</a> | <a href="README_CN.md">中文</a>
</p>

# Goals & Vocabulary Management System

A comprehensive personal goal management and English vocabulary learning platform, integrating Django REST Framework, FastAPI, and an **AI Chat Agent** powered by LangGraph and MCP (Model Context Protocol).

## 📋 Project Overview

This is a full-stack personal management application with the following main features:

- **🤖 AI Chat Agent** (NEW): Conversational XMeng powered by LangGraph that can manage your goals, tasks, and vocabulary through natural language
- **🎯 Goal Management**: Create, track, and manage personal goals with priority and status management
- **📝 Task Management**: Create specific actionable tasks for goals
- **📚 Vocabulary Learning**: Manage English vocabulary learning with multimedia content support
- **🏷️ Tag System**: Unified tag management for multiple use cases
- **🔐 User Authentication**: Secure JWT-based authentication system
- **📎 File Management**: Support for multiple file formats and media file uploads

## 🤖 AI Chat Agent

The system includes an intelligent conversational AI agent that allows users to manage all resources through natural language:

### Architecture

```
User (Text/Voice) → React Frontend → FastAPI SSE Endpoint → LangGraph Agent → OpenAI GPT-4o-mini
                                                                    ↓
                                                              MCP Tool Layer
                                                                    ↓
                                                          Django ORM (Database)
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| **LangGraph Agent** | `api/agent/graph.py` | ReAct-pattern stateful agent with tool-calling capabilities |
| **Agent Prompts** | `api/agent/prompts.py` | System prompt and conversation naming prompt |
| **Agent Tools** | `api/agent/tools.py` | 25 LangChain-compatible tools wrapping all CRUD operations |
| **MCP Server** | `api/mcp_server/server.py` | FastMCP server exposing tools via Model Context Protocol |
| **MCP Tool Functions** | `api/mcp_server/tools_goals.py`, `tools_words.py` | Async Django ORM wrappers for Goals/Tasks/Tags/Words |
| **Chat API** | `api/chat.py` | FastAPI router with SSE streaming for real-time AI responses |
| **Conversation Models** | `ai_chat/models.py` | Django models for Conversation and Message persistence |

### AI Capabilities

- **Natural Language CRUD**: Create, read, update, and delete Goals, Tasks, Goal Tags, English Words, and Word Tags through conversation
- **Intent Recognition**: Automatically recognizes user intent and invokes the appropriate MCP tools
- **Streaming Responses**: Real-time token-by-token streaming via Server-Sent Events (SSE)
- **Conversation Management**: Auto-summarized conversation names, persistent message history
- **General Q&A**: Handles general questions beyond business operations
- **Tool Transparency**: Users can see which tools are being called and their results

### Chat API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/chat/conversations` | List user conversations |
| `POST` | `/api/chat/conversations` | Create new conversation |
| `GET` | `/api/chat/conversations/{id}` | Get conversation with messages |
| `DELETE` | `/api/chat/conversations/{id}` | Delete conversation |
| `POST` | `/api/chat/conversations/{id}/messages` | Send message & stream AI response (SSE) |

### SSE Event Types

| Event | Description |
|-------|-------------|
| `token` | Streaming text token from AI |
| `tool_call` | AI is invoking a tool (name + arguments) |
| `tool_result` | Tool execution result |
| `done` | Stream complete (includes message_id, conversation_name) |
| `error` | Error occurred during processing |

## 🛠️ Tech Stack

### Backend
- **Django 4.2.21** - Main framework & ORM
- **FastAPI** - API service framework
- **Django REST Framework** - REST API
- **MySQL** - Database
- **Redis** - Cache (optional)
- **JWT** - User authentication

### AI & Agent
- **LangGraph** - Stateful AI agent framework (ReAct pattern)
- **LangChain + OpenAI** - LLM integration (GPT-4o-mini)
- **MCP (Model Context Protocol)** - Tool exposure protocol via FastMCP
- **SSE (Server-Sent Events)** - Real-time streaming responses

### Frontend Integration
- Supports modern frontend frameworks like React
- CORS configuration
- Static media file serving

### Development Tools
- **Django Debug Toolbar** - Debugging tool
- **django-extensions** - Django extensions
- **Locust** - Performance testing

## 🚀 Quick Start

### Requirements

- Python 3.8+
- MySQL 8.0+
- Redis (optional, for caching)
- OpenAI API Key (for AI Chat Agent)

### Installation Steps

1. **Clone the project**
   ```bash
   git clone https://github.com/himengmengmeng/tasks.git
   cd Goals
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-api.txt
   ```

4. **Configure environment variables**

   Copy the example file and fill in your keys:
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ```

5. **Database configuration**

   Create MySQL database:
   ```sql
   CREATE DATABASE tasks CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

   Modify database settings in `root_directory/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.mysql',
           'NAME': 'tasks',
           'HOST': 'localhost',
           'USER': 'your_username',
           'PASSWORD': 'your_password',
           'PORT': '3306',
       }
   }
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

### Starting the Services

You need to start **three services** for full functionality:

#### 1. Django Admin Server
```bash
python manage.py runserver
```
Access: http://127.0.0.1:8000/admin

#### 2. FastAPI Server (Main API + AI Chat)
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```
Access: http://127.0.0.1:8001

#### 3. MCP Server (Optional, for external MCP clients)
```bash
python -m api.mcp_server.run_server
```
Access: http://127.0.0.1:8002

> **Note**: The AI Chat Agent works without the standalone MCP server, as tools are invoked directly within the FastAPI process. The MCP server is only needed if you want to connect external MCP clients.

### API Documentation

After starting the FastAPI server, visit:
- **Swagger UI**: http://127.0.0.1:8001/docs

## 📚 API Endpoints

### Authentication (`/api/auth`)
- `POST /api/auth/token` - User login
- `POST /api/auth/register` - User registration
- `POST /api/auth/logout` - User logout
- `POST /api/auth/refresh` - Refresh token
- `GET /api/auth/me` - Get current user info

### AI Chat (`/api/chat`)
- `GET /api/chat/conversations` - List conversations
- `POST /api/chat/conversations` - Create conversation
- `GET /api/chat/conversations/{id}` - Get conversation detail with messages
- `DELETE /api/chat/conversations/{id}` - Delete conversation
- `POST /api/chat/conversations/{id}/messages` - Send message (SSE streaming response)

### Goals Management (`/api/goals`)
- `GET /api/goals/` - Get goals list
- `POST /api/goals/` - Create new goal
- `GET /api/goals/{id}` - Get goal details
- `PUT /api/goals/{id}` - Update goal
- `DELETE /api/goals/{id}` - Delete goal

### Tasks Management (`/api/tasks`)
- `GET /api/tasks/` - Get tasks list
- `POST /api/tasks/` - Create new task
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task

### Vocabulary Management (`/api/words`)
- `GET /api/words/` - Get words list
- `POST /api/words/` - Add new word
- `GET /api/words/{id}` - Get word details
- `PUT /api/words/{id}` - Update word
- `DELETE /api/words/{id}` - Delete word
- `POST /api/words/{id}/media` - Upload media file
- `DELETE /api/words/{id}/media/{media_id}` - Delete media file

### Tags Management (`/api/tags`)
- `GET /api/tags/` - Get tags list
- `POST /api/tags/` - Create new tag
- `GET /api/tags/{id}` - Get tag details
- `PUT /api/tags/{id}` - Update tag
- `DELETE /api/tags/{id}` - Delete tag

## 🔧 Configuration

### Environment Variables

Create a `.env` file (see `.env.example`):
```env
OPENAI_API_KEY=your-openai-api-key-here
```

### Media File Configuration

The project supports the following file formats:
- **Images**: jpg, jpeg, png, gif, bmp
- **Videos**: mp4, avi, mov, mkv
- **Documents**: pdf, doc, docx, xls, xlsx

Media files are stored in the `media/` directory, automatically organized by date.

## 🗄️ Data Models

### User Model (core.User)
- Extends Django User with additional user information

### Goal Model (goal_app.Goal)
- Title, description, status, priority, urgency
- Supports tag associations and file attachments

### Task Model (goal_app.Task)
- Task name, description, status, priority, urgency
- Can be linked to specific goals

### Word Model (main_app.EnglishWord)
- Word, definition, notes
- Supports multimedia files and tags

### Tag Model
- Unified tag system supporting goals, tasks, and words

### Conversation Model (ai_chat.Conversation)
- Conversation name (auto-summarized by LLM), creator, timestamps
- One-to-many relationship with Messages

### Message Model (ai_chat.Message)
- Role (human/ai), content, tool call details
- Foreign key to Conversation

## 🧪 Testing

Run unit tests:
```bash
python manage.py test
```

Run performance tests (requires Locust):
```bash
locust -f locustfile.py
```

## 🚀 Deployment

### Using Gunicorn
```bash
gunicorn root_directory.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker
```bash
docker build -t goals-app .
docker run -p 8000:8000 goals-app
```

## 🔗 Frontend

This backend is designed to work with the [Goals React Frontend](https://github.com/himengmengmeng/goals_react).

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Author

**Meng**

---

⭐ If this project helps you, please give it a star!
