from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def get_password_hash(password: str) -> str:
    salted = f"{settings.SECRET_KEY}:{password}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(get_password_hash(plain_password), hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vui lòng đăng nhập để thực hiện chức năng này")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không hợp lệ")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại hoặc đã bị khóa")
    return user

def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[User]:
    """Trả về User nếu token hợp lệ, ngược lại trả None (không chặn request).

    Dùng cho các endpoint vừa phục vụ khách vãng lai vừa cá nhân hoá cho hội viên
    (ví dụ: AI Coach cho phép dùng thử, nhưng tự động lưu hồ sơ nếu đã đăng nhập).
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return None
    return user


# ==========================================================================
# RBAC — 6 VAI TRÒ
# ==========================================================================
#: Nhóm quyền vận hành phòng tập (lễ tân, quản lý CSVC, admin, và bí danh staff cũ)
OPERATIONS_ROLES = (
    Role.RECEPTIONIST, Role.FACILITY_MANAGER, Role.ADMIN, Role.STAFF,
)
#: Nhóm quyền huấn luyện
TRAINER_ROLES = (Role.TRAINER, Role.ADMIN)


def require_operations(current_user: User = Depends(get_current_user)) -> User:
    """Lễ tân & Tư vấn viên, Quản lý CSVC, hoặc Quản trị viên.

    Dùng cho nghiệp vụ hợp đồng, POS, check-in cổng, tủ đồ, kho hàng.
    """
    if Role.normalize(current_user.role) not in OPERATIONS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Lễ tân, Quản lý cơ sở vật chất hoặc Quản trị viên mới có quyền thực hiện",
        )
    return current_user


def require_receptionist(current_user: User = Depends(get_current_user)) -> User:
    """Chỉ Lễ tân & Tư vấn viên (hoặc Admin)."""
    if Role.normalize(current_user.role) not in (Role.RECEPTIONIST, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Lễ tân & Tư vấn viên hoặc Quản trị viên mới có quyền thực hiện",
        )
    return current_user


def require_facility_manager(current_user: User = Depends(get_current_user)) -> User:
    """Chỉ Quản lý cơ sở vật chất (hoặc Admin)."""
    if Role.normalize(current_user.role) not in (Role.FACILITY_MANAGER, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản lý cơ sở vật chất hoặc Quản trị viên mới có quyền thực hiện",
        )
    return current_user


def require_staff_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Tương thích ngược: cho phép mọi vai trò vận hành + HLV."""
    role = Role.normalize(current_user.role)
    if role not in OPERATIONS_ROLES and role != Role.TRAINER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ nhân sự vận hành, Huấn luyện viên hoặc Quản trị viên mới có quyền thực hiện",
        )
    return current_user


def require_trainer_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Cho phép Huấn luyện viên và Quản trị viên (Dashboard HLV)."""
    if Role.normalize(current_user.role) not in TRAINER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Huấn luyện viên hoặc Quản trị viên mới có quyền thực hiện",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Chỉ Super Admin / Owner."""
    if Role.normalize(current_user.role) != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên (Admin) mới có quyền thực hiện",
        )
    return current_user
