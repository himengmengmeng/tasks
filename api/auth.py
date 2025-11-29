# === 使用 TYPE_CHECKING 的专业解决方案 ===
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm, HTTPBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import re
from django.contrib.auth import authenticate
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from asgiref.sync import sync_to_async
import logging

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
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

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
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
2. 获取 access_token
3. 在后续请求的 Header 中添加: `Authorization: Bearer <access_token>`

### 注意
令牌默认有效期为 24 小时
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
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@router.post(
    "/test-token", 
    response_model=UserResponse,
    summary="测试令牌",
    description="验证 JWT 令牌的有效性并返回当前用户信息",
    responses={
        200: {"description": "令牌有效"},
        401: {"description": "令牌无效或已过期"}
    }
)
async def test_token(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """测试令牌有效性"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        position=current_user.position,
        age=current_user.age
    )

@router.get(
    "/me", 
    response_model=UserResponse,
    summary="获取当前用户信息", 
    description="获取当前登录用户的详细信息",
    responses={
        200: {"description": "成功获取用户信息"},
        401: {"description": "未授权访问"}
    }
)
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

@router.get(
    "/check-username/{username}",
    summary="检查用户名可用性",
    description="检查用户名是否已被注册",
    responses={
        200: {"description": "检查完成"},
        422: {"description": "用户名格式无效"}
    }
)
async def check_username_availability(username: str):
    """检查用户名是否可用"""
    user = await async_get_user_by_username(username)
    return {
        "available": user is None,
        "username": username,
        "message": "用户名可用" if user is None else "用户名已被使用"
    }

@router.get(
    "/check-email/{email}",
    summary="检查邮箱可用性",
    description="检查邮箱地址是否已被注册", 
    responses={
        200: {"description": "检查完成"},
        422: {"description": "邮箱格式无效"}
    }
)
async def check_email_availability(email: str):
    """检查邮箱是否可用"""
    exists_result = await async_check_user_exists("", email)
    return {
        "available": not exists_result['email_exists'],
        "email": email,
        "message": "邮箱可用" if not exists_result['email_exists'] else "邮箱已被注册"
    }

@router.get(
    "/users",
    response_model=UserListResponse,
    summary="获取用户列表",
    description="""
获取系统用户列表（需要管理员权限）。

### 查询参数
- **page**: 页码，默认为 1
- **page_size**: 每页数量，默认为 20，最大 100
- **search**: 搜索关键词（用户名、邮箱、姓名）

### 权限要求
- 仅管理员可访问
    """,
    responses={
        200: {"description": "成功获取用户列表"},
        403: {"description": "权限不足"},
        500: {"description": "服务器内部错误"}
    }
)
async def get_users_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    admin_user: User = Depends(get_current_admin_user)
):
    """获取用户列表（管理员权限）"""
    try:
        result = await async_get_all_users(page, page_size, search)
        
        # 转换用户对象为响应模型
        users_response = [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                position=user.position,
                age=user.age
            )
            for user in result['users']
        ]
        
        return UserListResponse(
            users=users_response,
            total=result['total'],
            page=result['page'],
            page_size=result['page_size'],
            total_pages=result['total_pages']
        )
    except Exception as e:
        logger.error(f"Error in get_users_list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表时发生错误"
        )

@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="获取用户详情",
    description="""
获取指定用户的详细信息。

### 权限要求
- 管理员可以查看任何用户
- 普通用户只能查看自己的信息
    """,
    responses={
        200: {"description": "成功获取用户信息"},
        403: {"description": "权限不足"},
        404: {"description": "用户不存在"}
    }
)
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(check_user_permission)
):
    """获取用户详情"""
    user = await async_get_user_detail(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 确定用户权限
    permissions = []
    if user.is_staff:
        permissions.append("staff")
    if user.is_superuser:
        permissions.append("superuser")
    if user.is_active:
        permissions.append("active")
    
    return UserDetailResponse(
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            position=user.position,
            age=user.age
        ),
        permissions=permissions,
        is_owner=current_user.id == user_id
    )

@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="更新用户信息",
    description="""
更新用户信息。

### 可更新字段
- **email**: 邮箱地址
- **first_name**: 名字
- **last_name**: 姓氏
- **position**: 职位
- **age**: 年龄

### 权限要求
- 管理员可以更新任何用户
- 普通用户只能更新自己的信息
    """,
    responses={
        200: {"description": "用户信息更新成功"},
        400: {"description": "请求参数错误"},
        403: {"description": "权限不足"},
        404: {"description": "用户不存在"}
    }
)
async def update_user_info(
    user_id: int,
    update_data: UserUpdateRequest,
    current_user: User = Depends(check_user_permission)
):
    """更新用户信息"""
    try:
        # 过滤掉 None 值，只更新提供的字段
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供要更新的字段"
            )
        
        # 检查邮箱是否已被其他用户使用
        if 'email' in update_dict:
            email_exists = await sync_to_async(
                lambda: User.objects.filter(email=update_dict['email']).exclude(id=user_id).exists()
            )()
            if email_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被其他用户使用"
                )
        
        # 更新用户信息
        updated_user = await async_update_user(user_id, update_dict)
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            first_name=updated_user.first_name,
            last_name=updated_user.last_name,
            position=updated_user.position,
            age=updated_user.age
        )
        
    except ValueError as e:
        if "用户不存在" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息时发生错误"
        )

@router.put(
    "/me",
    response_model=UserResponse,
    summary="更新当前用户信息",
    description="""
更新当前登录用户自己的信息。

### 可更新字段
- **email**: 邮箱地址
- **first_name**: 名字
- **last_name**: 姓氏
- **position**: 职位
- **age**: 年龄
    """,
    responses={
        200: {"description": "用户信息更新成功"},
        400: {"description": "请求参数错误"}
    }
)
async def update_current_user_info(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """更新当前用户信息"""
    try:
        # 过滤掉 None 值，只更新提供的字段
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供要更新的字段"
            )
        
        # 检查邮箱是否已被其他用户使用
        if 'email' in update_dict:
            email_exists = await sync_to_async(
                lambda: User.objects.filter(email=update_dict['email']).exclude(id=current_user.id).exists()
            )()
            if email_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被其他用户使用"
                )
        
        # 更新用户信息
        updated_user = await async_update_user(current_user.id, update_dict)
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            email=updated_user.email,
            first_name=updated_user.first_name,
            last_name=updated_user.last_name,
            position=updated_user.position,
            age=updated_user.age
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating current user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息时发生错误"
        )