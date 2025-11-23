# === FastAPI 主应用 - 简化版本 ===
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

# 直接导入路由
import api.auth as auth_module
import api.goals as goals_module  
import api.words as words_module

app = FastAPI(title="Goals'APIs", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(auth_module.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(goals_module.router, prefix="/api/goals", tags=["Goals Management"])
app.include_router(words_module.router, prefix="/api/words", tags=["Vocabulary"])


@app.get("/")
async def root():
    return {"message": "FastAPI functions well", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)