<p align="center">
  <a href="README.md">English</a> | <a href="README_CN.md">中文</a>
</p>

# Goals & Vocabulary Management System

A comprehensive personal goal management and English vocabulary learning platform, integrating Django REST Framework and FastAPI technology stacks.

## 📋 Project Overview

This is a full-stack personal management application with the following main features:

- **🎯 Goal Management**: Create, track, and manage personal goals with priority and status management
- **📝 Task Management**: Create specific actionable tasks for goals
- **📚 Vocabulary Learning**: Manage English vocabulary learning with multimedia content support
- **🏷️ Tag System**: Unified tag management for multiple use cases
- **🔐 User Authentication**: Secure JWT-based authentication system
- **📎 File Management**: Support for multiple file formats and media file uploads

## 🛠️ Tech Stack

### Backend
- **Django 4.2.21** - Main framework
- **FastAPI** - API service framework
- **Django REST Framework** - REST API
- **MySQL** - Database
- **Redis** - Cache (optional)
- **JWT** - User authentication

### Frontend Integration
- Supports modern frontend frameworks like React/Vue
- CORS configuration
- Static media file serving

### Development Tools
- **Django Debug Toolbar** - Debugging tool
- **django-extensions** - Django extensions
- **OpenAI** - AI feature integration
- **Locust** - Performance testing

## 🚀 Quick Start

### Requirements

- Python 3.8+
- MySQL 8.0+
- Redis (optional, for caching)

### Installation Steps

1. **Clone the project**
   ```bash
   git clone https://github.com/himengmengmeng/tasks.git
   cd Goals
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Database configuration**

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

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

### Starting the Server

#### Option 1: Django Development Server
```bash
python manage.py runserver
```
Access: http://127.0.0.1:8000

#### Option 2: FastAPI Server (Recommended)
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```
Access: http://127.0.0.1:8001

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
- `POST /api/words/{id}/media` - Upload media file (images, videos, documents)
- `DELETE /api/words/{id}/media/{media_id}` - Delete media file

### Tags Management (`/api/tags`)
- `GET /api/tags/` - Get tags list
- `POST /api/tags/` - Create new tag
- `GET /api/tags/{id}` - Get tag details
- `PUT /api/tags/{id}` - Update tag
- `DELETE /api/tags/{id}` - Delete tag

## 🔧 Configuration

### Environment Variables

Create a `.env` file for sensitive information:
```env
SECRET_KEY=your-secret-key-here
DATABASE_NAME=tasks
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8001
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
# Build image
docker build -t goals-app .

# Run container
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
