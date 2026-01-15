# === 使用 TYPE_CHECKING 的专业解决方案 ===
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header, Request
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, validator, Field
import re
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from asgiref.sync import sync_to_async
import logging
from django.core.cache import cache

# 设置日志
logger = logging.getLogger(__name__)

# 🎯 专业类型检查配置
if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    # 运行时使用 get_user_model()
    User = get_user_model()

router = APIRouter()
security = HTTPBearer()

# 导入序列化器
try:
    from core.serializers import UserCreateSerializer
except ImportError:
    # 如果直接导入失败，尝试从core app导入
    try:
        from core.serializers import UserCreateSerializer
    except ImportError:
        # 最后尝试从auth app导入
        from core.serializers import UserCreateSerializer

# Pydantic 模型
class Token(BaseModel):
    access_token: str
    refresh_token: str  # 新增refresh token
    token_type: str = "bearer"
    expires_in: int = Field(default=604800)  # 7天，单位秒

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    user_id: int
    token_type: Optional[str] = "access"

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

# 注册请求模型
class UserRegisterRequest(BaseModel):
    username: str
    email: str  # 改为普通字符串
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = None

    @validator('email')
    def validate_email(cls, v):
        """自定义邮箱验证"""
        if not v:
            raise ValueError('邮箱不能为空')
        
        # 简单的邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式无效')
        
        return v

    @validator('password')
    def validate_password(cls, v):
        """密码强度验证"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

    @validator('username')
    def validate_username(cls, v):
        """用户名验证"""
        if len(v) < 3:
            raise ValueError('用户名长度至少3位')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

class UserRegisterResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    position: str
    age: Optional[int] = None
    message: str

    class Config:
        from_attributes = True

# 用户信息更新请求模型
class UserUpdateRequest(BaseModel):
    """用户信息更新请求模型"""
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    age: Optional[int] = None
    
    @validator('email')
    def validate_email(cls, v):
        """邮箱验证"""
        if v is not None:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('邮箱格式无效')
        return v

    @validator('age')
    def validate_age(cls, v):
        """年龄验证"""
        if v is not None and (v < 0 or v > 150):
            raise ValueError('年龄必须在0-150之间')
        return v

class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class UserDetailResponse(BaseModel):
    """用户详情响应模型"""
    user: UserResponse
    permissions: List[str] = []
    is_owner: bool = False

# JWT 配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30天

# ==================== Token 黑名单管理 ====================

def add_token_to_blacklist(token: str, token_type: str = "access"):
    """将token加入黑名单"""
    try:
        # 从token中提取JTI（JWT ID）
        jti = get_token_jti(token)
        if jti:
            # 根据token类型设置不同的过期时间
            if token_type == "access":
                expire_seconds = ACCESS_TOKEN_EXPIRE_MINUTES * 60
            else:  # refresh token
                expire_seconds = REFRESH_TOKEN_EXPIRE_MINUTES * 60
            
            # 使用Django缓存存储黑名单
            cache_key = f"token_blacklist:{jti}"
            cache.set(cache_key, "1", timeout=expire_seconds)
            logger.info(f"Token added to blacklist: {jti[:8]}..., type: {token_type}")
            return True
    except Exception as e:
        logger.error(f"Error adding token to blacklist: {str(e)}")
    return False

def is_token_blacklisted(token: str) -> bool:
    """检查token是否在黑名单中"""
    try:
        jti = get_token_jti(token)
        if not jti:
            return False
        
        cache_key = f"token_blacklist:{jti}"
        return cache.get(cache_key) is not None
    except Exception as e:
        logger.error(f"Error checking token blacklist: {str(e)}")
        return False

def get_token_jti(token: str) -> Optional[str]:
    """从token中提取JTI（JWT ID）"""
    try:
        # 不验证过期，只解析payload
        payload = jwt.get_unverified_claims(token)
        return payload.get("jti")
    except Exception:
        return None

def blacklist_user_tokens(user_id: int):
    """将用户的所有token加入黑名单"""
    try:
        # 这里可以扩展为存储用户与token的映射关系
        # 目前我们只记录一个标志，表示用户已登出所有设备
        cache_key = f"user_logged_out:{user_id}"
        cache.set(cache_key, "1", timeout=REFRESH_TOKEN_EXPIRE_MINUTES * 60)
        logger.info(f"All tokens blacklisted for user: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error blacklisting user tokens: {str(e)}")
        return False

def is_user_logged_out(user_id: int) -> bool:
    """检查用户是否已登出所有设备"""
    try:
        cache_key = f"user_logged_out:{user_id}"
        return cache.get(cache_key) is not None
    except Exception:
        return False

# ==================== 同步函数封装 ====================

def sync_authenticate_user(username: str, password: str) -> Optional[User]:
    """同步函数：用户认证"""
    try:
        return authenticate(username=username, password=password)
    except Exception as e:
        logger.error(f"Authentication error for user {username}: {str(e)}")
        return None

def sync_get_user_by_id(user_id: int) -> Optional[User]:
    """同步函数：根据ID获取用户"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting user by id {user_id}: {str(e)}")
        return None

def sync_check_user_exists(username: str, email: str) -> Dict[str, bool]:
    """同步函数：检查用户是否存在"""
    try:
        username_exists = User.objects.filter(username=username).exists()
        email_exists = User.objects.filter(email=email).exists()
        return {
            'username_exists': username_exists,
            'email_exists': email_exists
        }
    except Exception as e:
        logger.error(f"Error checking user existence: {str(e)}")
        return {'username_exists': False, 'email_exists': False}

def sync_create_user_with_serializer(user_data: Dict[str, Any]) -> User:
    """同步函数：使用序列化器创建用户"""
    serializer = UserCreateSerializer(data=user_data)
    
    if not serializer.is_valid():
        errors = serializer.errors
        logger.warning(f"User creation validation failed: {errors}")
        raise ValueError(f"Validation failed: {errors}")
    
    try:
        user = serializer.save()
        logger.info(f"User created successfully: {user.username}")
        return user
    except Exception as e:
        logger.error(f"Error creating user {user_data.get('username')}: {str(e)}")
        raise

def sync_get_user_by_username(username: str) -> Optional[User]:
    """同步函数：根据用户名获取用户"""
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting user by username {username}: {str(e)}")
        return None

def sync_get_all_users(page: int = 1, page_size: int = 20, search: str = None) -> Dict[str, Any]:
    """同步函数：获取所有用户（分页）"""
    try:
        users_query = User.objects.all().order_by('id')
        
        # 搜索功能
        if search:
            users_query = users_query.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search)
            )
        
        # 分页
        total = users_query.count()
        total_pages = (total + page_size - 1) // page_size
        
        # 确保页码在有效范围内
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages
            
        users = users_query[(page-1)*page_size : page*page_size]
        
        return {
            'users': list(users),
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
    except Exception as e:
        logger.error(f"Error getting user list: {str(e)}")
        raise

def sync_update_user(user_id: int, update_data: Dict[str, Any]) -> User:
    """同步函数：更新用户信息"""
    try:
        user = User.objects.get(id=user_id)
        
        # 准备更新字段
        update_fields = []
        for field, value in update_data.items():
            if value is not None and hasattr(user, field):
                setattr(user, field, value)
                update_fields.append(field)
        
        if update_fields:
            user.save(update_fields=update_fields)
            logger.info(f"User {user_id} updated fields: {update_fields}")
        
        return user
    except User.DoesNotExist:
        logger.warning(f"User {user_id} not found for update")
        raise ValueError("用户不存在")
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise

def sync_get_user_detail(user_id: int) -> Optional[User]:
    """同步函数：获取用户详情"""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting user detail {user_id}: {str(e)}")
        return None

# ==================== 异步包装器 ====================

async def async_authenticate(username: str, password: str) -> Optional[User]:
    """异步包装：用户认证"""
    return await sync_to_async(sync_authenticate_user)(username=username, password=password)

async def async_get_user(user_id: int) -> Optional[User]:
    """异步包装：根据ID获取用户"""
    return await sync_to_async(sync_get_user_by_id)(user_id)

async def async_check_user_exists(username: str, email: str) -> Dict[str, bool]:
    """异步包装：检查用户是否存在"""
    return await sync_to_async(sync_check_user_exists)(username, email)

async def async_create_user(user_data: Dict[str, Any]) -> User:
    """异步包装：创建用户"""
    return await sync_to_async(sync_create_user_with_serializer)(user_data)

async def async_get_user_by_username(username: str) -> Optional[User]:
    """异步包装：根据用户名获取用户"""
    return await sync_to_async(sync_get_user_by_username)(username)

async def async_get_all_users(page: int = 1, page_size: int = 20, search: str = None) -> Dict[str, Any]:
    """异步包装：获取所有用户"""
    return await sync_to_async(sync_get_all_users)(page, page_size, search)

async def async_update_user(user_id: int, update_data: Dict[str, Any]) -> User:
    """异步包装：更新用户信息"""
    return await sync_to_async(sync_update_user)(user_id, update_data)

async def async_get_user_detail(user_id: int) -> Optional[User]:
    """异步包装：获取用户详情"""
    return await sync_to_async(sync_get_user_detail)(user_id)

# ==================== JWT 工具函数 ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 添加JTI（JWT ID）用于token黑名单管理
    import uuid
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "token_type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    
    # 添加JTI（JWT ID）用于token黑名单管理
    import uuid
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "token_type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_refresh_token(refresh_token: str) -> Optional[Dict]:
    """验证refresh token"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 检查token类型
        if payload.get("token_type") != "refresh":
            return None
            
        # 检查是否在黑名单中
        if is_token_blacklisted(refresh_token):
            return None
            
        return payload
    except JWTError:
        return None

def decode_token(token: str) -> Optional[Dict]:
    """解码token（不验证过期）"""
    try:
        return jwt.get_unverified_claims(token)
    except Exception:
        return None

# ==================== 依赖注入 ====================

async def get_current_user(token: str = Depends(security)) -> User:
    """依赖项：从 JWT token 获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 检查token类型
        if payload.get("token_type") != "access":
            raise credentials_exception
            
        # 检查是否在黑名单中
        if is_token_blacklisted(token.credentials):
            raise credentials_exception
            
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
            
        # 检查用户是否已全局登出
        if is_user_logged_out(user_id):
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

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """依赖项：检查当前用户是否为管理员"""
    if not current_user.is_staff and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user

async def check_user_permission(
    user_id: int, 
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    依赖项：检查用户权限
    - 管理员可以访问任何用户
    - 普通用户只能访问自己的信息
    """
    if current_user.is_staff or current_user.is_superuser or current_user.id == user_id:
        return current_user
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问该用户信息"
        )

# ==================== 路由处理 ====================

@router.post(
    "/register", 
    response_model=UserRegisterResponse,
    summary="用户注册",
    description="""
注册新用户账户。

### 参数说明
- **username**: 用户名，必须唯一，至少3位，只能包含字母、数字和下划线
- **email**: 邮箱地址，必须唯一且有效格式
- **password**: 密码，至少6位
- **first_name**: 名字（可选）
- **last_name**: 姓氏（可选） 
- **position**: 职位（可选）
- **age**: 年龄（可选）

### 返回信息
- 注册成功的用户信息
    """,
    responses={
        200: {"description": "用户注册成功"},
        400: {"description": "用户名或邮箱已存在"},
        422: {"description": "请求参数验证失败"},
        500: {"description": "服务器内部错误"}
    }
)
async def register_user(user_data: UserRegisterRequest):
    """
    用户注册端点
    """
    # 检查用户名和邮箱是否已存在
    exists_result = await async_check_user_exists(user_data.username, user_data.email)
    
    if exists_result['username_exists']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    if exists_result['email_exists']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 准备用户数据
    user_dict = {
        'username': user_data.username,
        'email': user_data.email,
        'password': user_data.password,
        'first_name': user_data.first_name or '',
        'last_name': user_data.last_name or '',
        'position': user_data.position or '',
        'age': user_data.age
    }
    
    # 创建用户
    try:
        user = await async_create_user(user_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"注册验证失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during user registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建用户时发生服务器错误"
        )
    
    return UserRegisterResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        position=user.position,
        age=user.age,
        message="用户注册成功"
    )

@router.post(
    "/token", 
    response_model=Token,
    summary="用户登录",
    description="""
用户登录获取 JWT 访问令牌。

### 使用说明
1. 使用用户名和密码登录
2. 获取 access_token 和 refresh_token
3. 在后续请求的 Header 中添加: `Authorization: Bearer <access_token>`

### 注意
- access_token 有效期为 7 天
- refresh_token 有效期为 30 天，用于刷新 access_token
    """,
    responses={
        200: {"description": "登录成功，返回访问令牌"},
        401: {"description": "用户名或密码错误"},
        422: {"description": "请求参数验证失败"}
    }
)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """用户登录获取访问令牌"""
    # 使用异步认证函数
    user = await async_authenticate(username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    # 清除用户的全局登出状态（如果存在）
    cache_key = f"user_logged_out:{user.id}"
    cache.delete(cache_key)
    
    # 创建access token和refresh token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"user_id": user.id}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id}, expires_delta=refresh_token_expires
    )
    
    return Token(
        access_token=access_token, 
        refresh_token=refresh_token, 
        token_type="bearer",
        expires_in=7*24*60*60  # 7天的秒数
    )

@router.post(
    "/refresh",
    response_model=Token,
    summary="刷新访问令牌",
    description="""
使用refresh token刷新access token。

### 使用说明
1. 当access token过期时，使用refresh token获取新的access token
2. refresh token的有效期为30天
3. 刷新后，旧的refresh token会被加入黑名单

### 注意
refresh token只能使用一次，刷新后会生成新的refresh token
    """,
    responses={
        200: {"description": "刷新成功，返回新的令牌"},
        401: {"description": "refresh token无效或已过期"},
        422: {"description": "请求参数验证失败"}
    }
)
async def refresh_access_token(refresh_request: RefreshTokenRequest):
    """刷新access token"""
    # 验证refresh token
    payload = verify_refresh_token(refresh_request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的refresh token"
        )
    
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的refresh token"
        )
    
    # 检查用户是否已全局登出
    if is_user_logged_out(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已登出所有设备，请重新登录"
        )
    
    # 获取用户
    user = await async_get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    
    # 将旧的refresh token加入黑名单
    add_token_to_blacklist(refresh_request.refresh_token, "refresh")
    
    # 创建新的access token和refresh token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = create_access_token(
        data={"user_id": user.id}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id}, expires_delta=refresh_token_expires
    )
    
    return Token(
        access_token=access_token, 
        refresh_token=refresh_token, 
        token_type="bearer",
        expires_in=7*24*60*60  # 7天的秒数
    )

@router.post(
    "/logout",
    summary="用户登出",
    description="""
用户登出，将当前token加入黑名单。

### 使用说明
1. 需要提供当前使用的access token（通过Authorization header）
2. 可选：提供refresh token以将其也加入黑名单
3. 登出后，提供的token将无法再使用

### 注意
登出后，客户端应删除本地存储的token
    """,
    responses={
        200: {"description": "登出成功"},
        401: {"description": "未授权访问"}
    }
)
async def logout_user(
    request: Request,
    logout_data: Optional[LogoutRequest] = None,
    current_user: User = Depends(get_current_active_user),
    authorization: Optional[str] = Header(None)
):
    """用户登出"""
    try:
        # 获取当前请求的access token
        if authorization and authorization.startswith("Bearer "):
            access_token = authorization[7:]  # 移除"Bearer "前缀
            
            # 将access token加入黑名单
            if add_token_to_blacklist(access_token, "access"):
                logger.info(f"Access token blacklisted for user: {current_user.id}")
        
        # 如果提供了refresh token，也将其加入黑名单
        if logout_data and logout_data.refresh_token:
            refresh_payload = decode_token(logout_data.refresh_token)
            if refresh_payload and refresh_payload.get("user_id") == current_user.id:
                add_token_to_blacklist(logout_data.refresh_token, "refresh")
                logger.info(f"Refresh token blacklisted for user: {current_user.id}")
        
        return {
            "message": "登出成功",
            "detail": "token已加入黑名单，客户端请删除本地存储的token"
        }
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出时发生错误"
        )

@router.post(
    "/logout-all",
    summary="全部登出",
    description="""
使当前用户的所有token失效。

### 使用说明
1. 此操作会使该用户的所有access token和refresh token失效
2. 用户需要重新登录获取新的token
3. 此操作不可逆

### 注意
仅建议在安全事件（如设备丢失）时使用
    """,
    responses={
        200: {"description": "全部登出成功"},
        401: {"description": "未授权访问"}
    }
)
async def logout_all_devices(
    current_user: User = Depends(get_current_active_user)
):
    """使当前用户的所有token失效"""
    # 标记用户为已全局登出
    if blacklist_user_tokens(current_user.id):
        return {
            "message": "全部登出成功",
            "detail": "所有设备的token已失效，需要重新登录"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="全部登出操作失败"
        )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
    description="""
获取当前登录用户的详细信息。

### 使用说明
需要在 Header 中提供有效的 access_token

### 返回信息
- 用户ID、用户名、邮箱等基本信息
    """,
    responses={
        200: {"description": "成功返回用户信息"},
        401: {"description": "未授权访问"}
    }
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """获取当前用户信息"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        position=getattr(current_user, 'position', ''),
        age=getattr(current_user, 'age', None)
    )