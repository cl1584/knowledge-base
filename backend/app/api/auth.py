"""Auth API：注册、登录、获取当前用户"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# === 简易内存限流（单进程有效；多 worker 部署需 Redis 共享） ===
# 同一 IP 在 60 秒内最多 5 次登录失败，封禁 5 分钟
# uvicorn --workers N 时，每个 worker 独立计数，攻击者可能绕过；
# 生产建议换 slowapi/limits + Redis，或单 worker。
_login_attempts: dict[str, list[float]] = defaultdict(list)
_login_blocked: dict[str, float] = {}
_login_lock = Lock()
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 60
BLOCK_SECONDS = 300


def _check_login_rate_limit(ip: str) -> None:
    now = time.time()
    with _login_lock:
        blocked_until = _login_blocked.get(ip)
        if blocked_until and blocked_until > now:
            raise HTTPException(
                status_code=429,
                detail=f"登录失败次数过多，请 {int((blocked_until - now) / 60) + 1} 分钟后再试",
            )
        _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < WINDOW_SECONDS]


def _record_login_attempt(ip: str, success: bool) -> None:
    now = time.time()
    with _login_lock:
        if success:
            _login_attempts.pop(ip, None)
            _login_blocked.pop(ip, None)
            return
        _login_attempts[ip].append(now)
        if len(_login_attempts[ip]) >= MAX_ATTEMPTS:
            _login_blocked[ip] = now + BLOCK_SECONDS
            _login_attempts[ip] = []


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从 Bearer token 解析当前用户"""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 无效或已过期")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 缺少用户 ID")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户（v1 单用户场景）"""
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        nickname=req.nickname or req.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, {"username": user.username})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """账号密码登录（含失败限流）"""
    # 拿客户端 IP（处理反向代理）
    client_ip = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP", "").strip()
        or (request.client.host if request.client else "unknown")
    )
    _check_login_rate_limit(client_ip)

    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        _record_login_attempt(client_ip, success=False)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    _record_login_attempt(client_ip, success=True)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token(user.id, {"username": user.username})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user
