# === FastAPI 主应用 - 调整文档顺序 ===
import os
import django
import sys
from pathlib import Path


# 设置正确的路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root_directory.settings')
django.setup()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 导入所有路由
import api.auth as auth_module
import api.goals as goals_module  
import api.words as words_module
import api.tags as tags_module
import api.tasks as tasks_module
import api.chat as chat_module

app = FastAPI(
    title="Goals'APIs",
    description="Meng's Goals & Tasks Management API",
    version="2.0.0",
    docs_url="/docs",
    
    # 新增配置：隐藏 Schemas 部分
    swagger_ui_parameters={
        "deepLinking": True,
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": -1 , # 隐藏 Schemas 部
    }
)


# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 调整路由包含顺序 ====================
# 按照您想要的顺序包含路由，这会影响文档中的显示顺序

# 1. Authentication (保持不变)
app.include_router(auth_module.router, prefix="/api/auth", tags=["Authentication"])

# 2. Goals Management (保持不变)
app.include_router(goals_module.router, prefix="/api/goals", tags=["Goals Management"])

# 3. Tasks Management (调整到第三位)
app.include_router(tasks_module.router, prefix="/api/tasks", tags=["Tasks Management"])

# 4. Vocabulary Management (调整到第四位)
app.include_router(words_module.router, prefix="/api/words", tags=["Vocabulary Management"])

# 5. Tags Management (调整到最后)
app.include_router(tags_module.router, prefix="/api/tags", tags=["Tags Management"])

# 6. AI Chat
app.include_router(chat_module.router, prefix="/api/chat", tags=["AI Chat"])

# 挂载媒体文件
from django.conf import settings
app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")

@app.get("/")
async def root():
    return {
        "message": "Goals & Vocabulary API 运行正常", 
        "status": "healthy",
        "version": "2.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "goals": "/api/goals",
            "tasks": "/api/tasks",
            "words": "/api/words",
            "tags": "/api/tags",
            "chat": "/api/chat",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": __import__("datetime").datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.FASTAPI_HOST, 
        port=settings.FASTAPI_PORT, 
        reload=settings.FASTAPI_RELOAD
    )