# === words.py 的 TYPE_CHECKING 版本 ===
from typing import TYPE_CHECKING, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist

from .auth import get_current_active_user
from main_app.models import EnglishWord, Tag

# 🎯 专业类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    from django.contrib.auth import get_user_model
    User = get_user_model()

router = APIRouter()

# Pydantic 模型和函数定义...
# 在所有使用 User 类型的地方都可以正常使用