import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from shared.models.database import get_db
from shared.models.user import User
from shared.services.auth_utils import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# SameSite=None is required for cross-origin cookies (Vercel → Render)
_IS_PROD = os.getenv("ENVIRONMENT", "development") == "production"
_COOKIE = dict(httponly=True, secure=_IS_PROD, samesite="none" if _IS_PROD else "lax")
_ACCESS_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
_REFRESH_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 86400


class _RegisterBody(BaseModel):
    name: str
    email: EmailStr
    password: str


class _LoginBody(BaseModel):
    email: EmailStr
    password: str


def _set_auth_cookies(response: Response, user_id: int) -> None:
    response.set_cookie("access_token", create_access_token(user_id), max_age=_ACCESS_MAX_AGE, **_COOKIE)
    response.set_cookie("refresh_token", create_refresh_token(user_id), max_age=_REFRESH_MAX_AGE, **_COOKIE)


def _public_user(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email}


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: _RegisterBody, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = User(
        name=body.name.strip(),
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _set_auth_cookies(response, user.id)
    return {"user": _public_user(user)}


@router.post("/login")
def login(body: _LoginBody, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # Constant-time check prevents user enumeration via timing
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _set_auth_cookies(response, user.id)
    return {"user": _public_user(user)}


@router.get("/me")
def me(access_token: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        user_id = decode_access_token(access_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return _public_user(user)


@router.post("/refresh")
def refresh(
    refresh_token: str | None = Cookie(default=None),
    response: Response = None,
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token.")
    try:
        user_id = decode_refresh_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    _set_auth_cookies(response, user.id)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", **_COOKIE)
    response.delete_cookie("refresh_token", **_COOKIE)
    return {"ok": True}
