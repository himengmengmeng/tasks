# === 使用 TYPE_CHECKING 的专业解决方案 ===
from typing import TYPE_CHECKING, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async  # 新增导入

# 🎯 专业类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    # 运行时使用 get_user_model()
    User = get_user_model()

router = APIRouter()
security = HTTPBearer()

# Pydantic 模型
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    position: str
    age: Optional[int] = None
    
    class Config:
        from_attributes = True

# JWT 配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 创建异步的 authenticate 函数
async def async_authenticate(username: str, password: str) -> Optional[User]:
    """异步的用户认证"""
    return await sync_to_async(authenticate)(username=username, password=password)

# 创建异步的 User 查询函数
async def async_get_user(user_id: int) -> Optional[User]:
    """异步获取用户"""
    return await sync_to_async(User.objects.filter(id=user_id).first)()

async def get_current_user(token: str = Depends(security)) -> User:
    """依赖项：从 JWT token 获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    # 🎯 使用异步方式获取用户
    user = await async_get_user(token_data.user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """依赖项：获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """user login to get access token"""
    # 使用异步认证函数
    user = await async_authenticate(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@router.post("/test-token", response_model=UserResponse)
async def test_token(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """test token's validity"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        position=current_user.position,
        age=current_user.age
    )

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        position=current_user.position,
        age=current_user.age
    )