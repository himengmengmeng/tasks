# Goals & Vocabulary Management System

一个综合性的个人目标管理和英语词汇学习平台，集成了Django REST Framework和FastAPI技术栈。

## 📋 项目概述

这是一个全栈个人管理应用，主要功能包括：

- **🎯 目标管理**：创建、跟踪和管理个人目标，支持优先级和状态管理
- **📝 任务管理**：为目标创建具体可执行的任务
- **📚 词汇学习**：管理英语单词学习，支持多媒体内容
- **🏷️ 标签系统**：统一的标签管理，支持多场景使用
- **🔐 用户认证**：安全的JWT身份认证系统
- **📎 文件管理**：支持多种格式的附件上传和媒体文件管理

## 🛠️ 技术栈

### 后端
- **Django 4.2.21** - 主框架
- **FastAPI** - API服务框架
- **Django REST Framework** - REST API
- **MySQL** - 数据库
- **Redis** - 缓存（可选）
- **JWT** - 用户认证

### 前端集成
- 支持React/Vue等现代前端框架
- CORS跨域配置
- 媒体文件静态服务

### 开发工具
- **Django Debug Toolbar** - 调试工具
- **django-extensions** - Django扩展
- **OpenAI** - AI功能集成
- **Locust** - 性能测试

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 8.0+
- Redis (可选，用于缓存)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd Goals
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **数据库配置**

   创建MySQL数据库：
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

5. **运行迁移**
   ```bash
   python manage.py migrate
   ```

6. **创建超级用户**
   ```bash
   python manage.py createsuperuser
   ```

### 启动服务

#### 方式一：Django开发服务器
```bash
python manage.py runserver
```
访问: http://127.0.0.1:8000

#### 方式二：FastAPI服务器（推荐）
```bash
python api/main.py
```
访问: http://127.0.0.1:8001

### API文档

启动FastAPI服务器后，访问以下地址查看API文档：
**Swagger UI**: http://127.0.0.1:8001/docs


## 📚 API 接口

### 认证接口 (`/api/auth`)
- `POST /api/auth/login/` - 用户登录
- `POST /api/auth/register/` - 用户注册
- `POST /api/auth/logout/` - 用户登出

### 目标管理 (`/api/goals`)
- `GET /api/goals/` - 获取目标列表
- `POST /api/goals/` - 创建新目标
- `GET /api/goals/{id}/` - 获取目标详情
- `PUT /api/goals/{id}/` - 更新目标
- `DELETE /api/goals/{id}/` - 删除目标

### 任务管理 (`/api/tasks`)
- `GET /api/tasks/` - 获取任务列表
- `POST /api/tasks/` - 创建新任务
- `GET /api/tasks/{id}/` - 获取任务详情
- `PUT /api/tasks/{id}/` - 更新任务
- `DELETE /api/tasks/{id}/` - 删除任务

### 词汇管理 (`/api/words`)
- `GET /api/words/` - 获取单词列表
- `POST /api/words/` - 添加新单词
- `GET /api/words/{id}/` - 获取单词详情
- `PUT /api/words/{id}/` - 更新单词
- `DELETE /api/words/{id}/` - 删除单词
- `POST /api/words/{id}/media` - 上传媒体文件（支持图片、视频、文档）
- `DELETE /api/words/{id}/media/{media_id}` - 删除媒体文件

### 标签管理 (`/api/tags`)
- `GET /api/tags/` - 获取标签列表
- `POST /api/tags/` - 创建新标签
- `GET /api/tags/{id}/` - 获取标签详情
- `PUT /api/tags/{id}/` - 更新标签
- `DELETE /api/tags/{id}/` - 删除标签

## 🔧 配置说明

### 环境变量

创建 `.env` 文件配置敏感信息：
```env
SECRET_KEY=your-secret-key-here
DATABASE_NAME=tasks
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8001
```

### 媒体文件配置

项目支持以下格式的附件上传：
- **图片**: jpg, jpeg, png, gif, bmp
- **视频**: mp4, avi, mov, mkv
- **文档**: pdf, doc, docx, xls, xlsx

媒体文件存储在 `media/` 目录下，按日期自动组织。

## 🗄️ 数据模型

### 用户模型 (core.User)
- 继承Django User，扩展用户信息

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

## 🧪 测试

运行单元测试：
```bash
python manage.py test
```

运行性能测试（需要安装Locust）：
```bash
locust -f locustfile.py
```

## 🚀 部署

### 使用Gunicorn部署
```bash
gunicorn root_directory.wsgi:application --bind 0.0.0.0:8000
```

### 使用Docker部署
```bash
# 构建镜像
docker build -t goals-app .

# 运行容器
docker run -p 8000:8000 goals-app
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 👨‍💻 作者

**Meng**

## 🙏 致谢

- Django社区
- FastAPI团队
- 所有贡献者

---

⭐ 如果这个项目对你有帮助，请给它一个星标！
