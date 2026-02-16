<p align="center">
  <a href="README.md">English</a> | <a href="README_CN.md">中文</a>
</p>

# Goals 目标与词汇管理系统

一个综合性的个人目标管理和英语词汇学习平台，集成了 Django REST Framework、FastAPI，以及基于 **LangGraph 和 MCP（模型上下文协议）** 的 **AI 智能对话助手**。

## 📋 项目概述

这是一个全栈个人管理应用，主要功能包括：

- **🤖 AI 智能对话助手**（新功能）：基于 LangGraph 的对话式 AI 助手，支持通过自然语言管理目标、任务和词汇
- **🎯 目标管理**：创建、跟踪和管理个人目标，支持优先级和状态管理
- **📝 任务管理**：为目标创建具体可执行的任务
- **📚 词汇学习**：管理英语单词学习，支持多媒体内容
- **🏷️ 标签系统**：统一的标签管理，支持多场景使用
- **🔐 用户认证**：安全的 JWT 身份认证系统
- **📎 文件管理**：支持多种格式的附件上传和媒体文件管理

## 🤖 AI 智能对话助手

系统内置了一个智能对话 AI 助手，用户可以通过自然语言来管理所有资源：

### 架构设计

```
用户 (文字/语音) → React 前端 → FastAPI SSE 接口 → LangGraph Agent → OpenAI GPT-4o-mini
                                                          ↓
                                                    MCP 工具层
                                                          ↓
                                                  Django ORM (数据库)
```

### 核心组件

| 组件 | 位置 | 说明 |
|------|------|------|
| **LangGraph Agent** | `api/agent/graph.py` | 基于 ReAct 模式的有状态智能体，支持工具调用 |
| **Agent 提示词** | `api/agent/prompts.py` | 系统提示词和对话命名提示词 |
| **Agent 工具集** | `api/agent/tools.py` | 25 个 LangChain 兼容工具，封装所有 CRUD 操作 |
| **MCP 服务器** | `api/mcp_server/server.py` | FastMCP 服务器，通过模型上下文协议暴露工具 |
| **MCP 工具函数** | `api/mcp_server/tools_goals.py`, `tools_words.py` | 异步 Django ORM 封装（目标/任务/标签/单词） |
| **对话 API** | `api/chat.py` | FastAPI 路由，支持 SSE 流式传输实时 AI 响应 |
| **对话模型** | `ai_chat/models.py` | Django 模型，用于持久化对话和消息记录 |

### AI 功能特性

- **自然语言 CRUD**：通过对话创建、查询、更新和删除目标、任务、目标标签、英语单词和单词标签
- **意图识别**：自动识别用户意图并调用相应的 MCP 工具
- **流式响应**：通过 Server-Sent Events (SSE) 实现逐字实时流式输出
- **对话管理**：AI 自动总结对话名称，持久化消息历史
- **通用问答**：除业务操作外，还能处理通用知识问答
- **工具透明**：用户可以看到 AI 正在调用哪些工具及其结果

### 对话 API 接口

| 方法 | 接口 | 说明 |
|------|------|------|
| `GET` | `/api/chat/conversations` | 获取用户对话列表 |
| `POST` | `/api/chat/conversations` | 创建新对话 |
| `GET` | `/api/chat/conversations/{id}` | 获取对话详情及消息 |
| `DELETE` | `/api/chat/conversations/{id}` | 删除对话 |
| `POST` | `/api/chat/conversations/{id}/messages` | 发送消息并流式返回 AI 响应 (SSE) |

### SSE 事件类型

| 事件 | 说明 |
|------|------|
| `token` | AI 流式输出的文本片段 |
| `tool_call` | AI 正在调用工具（工具名称 + 参数） |
| `tool_result` | 工具执行结果 |
| `done` | 流式传输完成（包含 message_id、conversation_name） |
| `error` | 处理过程中发生错误 |

## 🛠️ 技术栈

### 后端
- **Django 4.2.21** - 主框架 & ORM
- **FastAPI** - API 服务框架
- **Django REST Framework** - REST API
- **MySQL** - 数据库
- **Redis** - 缓存（可选）
- **JWT** - 用户认证

### AI & Agent
- **LangGraph** - 有状态 AI 智能体框架（ReAct 模式）
- **LangChain + OpenAI** - LLM 集成（GPT-4o-mini）
- **MCP（模型上下文协议）** - 通过 FastMCP 暴露工具
- **SSE（Server-Sent Events）** - 实时流式响应

### 前端集成
- 支持 React 等现代前端框架
- CORS 跨域配置
- 媒体文件静态服务

### 开发工具
- **Django Debug Toolbar** - 调试工具
- **django-extensions** - Django 扩展
- **Locust** - 性能测试

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 8.0+
- Redis（可选，用于缓存）
- OpenAI API Key（AI 对话助手所需）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/himengmengmeng/tasks.git
   cd Goals
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate     # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-api.txt
   ```

4. **配置环境变量**

   复制示例文件并填入你的密钥：
   ```bash
   cp .env.example .env
   ```

   编辑 `.env`：
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ```

5. **数据库配置**

   创建 MySQL 数据库：
   ```sql
   CREATE DATABASE tasks CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

   修改 `root_directory/settings.py` 中的数据库配置：
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

6. **运行迁移**
   ```bash
   python manage.py migrate
   ```

7. **创建超级用户**
   ```bash
   python manage.py createsuperuser
   ```

### 启动服务

完整功能需要启动 **三个服务**：

#### 1. Django 管理后台
```bash
python manage.py runserver
```
访问: http://127.0.0.1:8000/admin

#### 2. FastAPI 服务器（主 API + AI 对话）
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```
访问: http://127.0.0.1:8001

#### 3. MCP 服务器（可选，供外部 MCP 客户端连接）
```bash
python -m api.mcp_server.run_server
```
访问: http://127.0.0.1:8002

> **提示**：AI 对话助手无需单独启动 MCP 服务器即可工作，因为工具在 FastAPI 进程内直接调用。MCP 服务器仅在需要连接外部 MCP 客户端时才需要启动。

### API 文档

启动 FastAPI 服务器后，访问：
- **Swagger UI**: http://127.0.0.1:8001/docs

## 📚 API 接口

### 认证接口 (`/api/auth`)
- `POST /api/auth/token` - 用户登录
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/logout` - 用户登出
- `POST /api/auth/refresh` - 刷新令牌
- `GET /api/auth/me` - 获取当前用户信息

### AI 对话接口 (`/api/chat`)
- `GET /api/chat/conversations` - 获取对话列表
- `POST /api/chat/conversations` - 创建对话
- `GET /api/chat/conversations/{id}` - 获取对话详情及消息
- `DELETE /api/chat/conversations/{id}` - 删除对话
- `POST /api/chat/conversations/{id}/messages` - 发送消息（SSE 流式响应）

### 目标管理 (`/api/goals`)
- `GET /api/goals/` - 获取目标列表
- `POST /api/goals/` - 创建新目标
- `GET /api/goals/{id}` - 获取目标详情
- `PUT /api/goals/{id}` - 更新目标
- `DELETE /api/goals/{id}` - 删除目标

### 任务管理 (`/api/tasks`)
- `GET /api/tasks/` - 获取任务列表
- `POST /api/tasks/` - 创建新任务
- `GET /api/tasks/{id}` - 获取任务详情
- `PUT /api/tasks/{id}` - 更新任务
- `DELETE /api/tasks/{id}` - 删除任务

### 词汇管理 (`/api/words`)
- `GET /api/words/` - 获取单词列表
- `POST /api/words/` - 添加新单词
- `GET /api/words/{id}` - 获取单词详情
- `PUT /api/words/{id}` - 更新单词
- `DELETE /api/words/{id}` - 删除单词
- `POST /api/words/{id}/media` - 上传媒体文件
- `DELETE /api/words/{id}/media/{media_id}` - 删除媒体文件

### 标签管理 (`/api/tags`)
- `GET /api/tags/` - 获取标签列表
- `POST /api/tags/` - 创建新标签
- `GET /api/tags/{id}` - 获取标签详情
- `PUT /api/tags/{id}` - 更新标签
- `DELETE /api/tags/{id}` - 删除标签

## 🔧 配置说明

### 环境变量

创建 `.env` 文件（参见 `.env.example`）：
```env
OPENAI_API_KEY=your-openai-api-key-here
```

### 媒体文件配置

项目支持以下格式的附件上传：
- **图片**: jpg, jpeg, png, gif, bmp
- **视频**: mp4, avi, mov, mkv
- **文档**: pdf, doc, docx, xls, xlsx

媒体文件存储在 `media/` 目录下，按日期自动组织。

## 🗄️ 数据模型

### 用户模型 (core.User)
- 继承 Django User，扩展用户信息

### 目标模型 (goal_app.Goal)
- 标题、描述、状态、优先级、紧急度
- 支持标签关联和附件上传

### 任务模型 (goal_app.Task)
- 任务名称、描述、状态、优先级、紧急度
- 可关联到具体目标

### 单词模型 (main_app.EnglishWord)
- 单词、释义、笔记
- 支持多媒体文件和标签

### 标签模型
- 统一的标签系统，支持目标、任务和单词

### 对话模型 (ai_chat.Conversation)
- 对话名称（LLM 自动总结）、创建者、时间戳
- 与消息为一对多关系

### 消息模型 (ai_chat.Message)
- 角色（human/ai）、内容、工具调用详情
- 外键关联到对话

## 🧪 测试

运行单元测试：
```bash
python manage.py test
```

运行性能测试（需要安装 Locust）：
```bash
locust -f locustfile.py
```

## 🚀 部署

### 使用 Gunicorn 部署
```bash
gunicorn root_directory.wsgi:application --bind 0.0.0.0:8000
```

### 使用 Docker 部署
```bash
docker build -t goals-app .
docker run -p 8000:8000 goals-app
```

## 🔗 前端项目

本后端设计用于配合 [Goals React 前端](https://github.com/himengmengmeng/goals_react) 使用。

## 📄 许可证

本项目采用 MIT 许可证。

## 👨‍💻 作者

**Meng**

---

⭐ 如果这个项目对你有帮助，请给它一个星标！
