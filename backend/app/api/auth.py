from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import jwt
import logging

from app.config import settings
from app.db.utils import create_user, get_user_by_email, verify_password
from app.utils.email_utils import send_welcome_email
from fastapi.concurrency import run_in_threadpool


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    token: str | None = None
    user: dict | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _create_jwt_token(user_id: int, email: str, name: str | None = None) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)).timestamp()),
    }
    if name:
        payload["name"] = name
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post("/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    try:
        existing = get_user_by_email(req.email)
        if existing:
            return AuthResponse(success=False, message="Email already registered")

        # Trim possible trailing spaces that may come from UI copy/paste
        password = req.password.strip()
        user = create_user(req.name, req.email, password)
        token = _create_jwt_token(user_id=user["id"], email=user["email"], name=user.get("name"))  # RealDictCursor
        # Fire-and-forget welcome email
        try:
            run_in_threadpool(send_welcome_email, user["email"], user.get("name"))
        except Exception:
            pass
        return AuthResponse(success=True, message="Signup successful", token=token, user={"id": user["id"], "name": user["name"], "email": user["email"]})
    except Exception as e:
        logger.exception("Signup failed: %s", e)
        detail = str(e) if getattr(settings, "DEBUG", False) else None
        return AuthResponse(success=False, message=detail or "Signup failed. Please try again.")


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    try:
        user = get_user_by_email(req.email)
        if not user or not verify_password(req.password, user["password_hash"]):
            return AuthResponse(success=False, message="Invalid credentials")

        token = _create_jwt_token(user_id=user["id"], email=user["email"], name=user.get("name"))  # RealDictCursor
        return AuthResponse(success=True, message="Login successful", token=token, user={"id": user["id"], "name": user["name"], "email": user["email"]})
    except Exception as e:
        logger.exception("Login failed: %s", e)
        detail = str(e) if getattr(settings, "DEBUG", False) else None
        return AuthResponse(success=False, message=detail or "Login failed. Please try again.")


