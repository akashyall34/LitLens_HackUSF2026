import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.utils import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db import SessionLocal
from app.demo_workspace import ensure_demo_workspace_for_user

router = APIRouter(prefix="/auth", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _issue_refresh_token(user_id: str, db: Session) -> str:
    """Create a refresh token, store its hash, return the plain token."""
    token = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.execute(
        text("""
            INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
            VALUES (CAST(:uid AS UUID), :hash, :exp)
        """),
        {"uid": user_id, "hash": hash_token(token), "exp": expires_at},
    )
    db.commit()
    return token


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()

    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO users (id, email, full_name, password_hash)
            VALUES (CAST(:id AS UUID), :email, :full_name, :password_hash)
        """),
        {
            "id": user_id,
            "email": email,
            "full_name": body.full_name,
            "password_hash": hash_password(body.password),
        },
    )
    ensure_demo_workspace_for_user(db, user_id)
    db.commit()

    return {
        "access_token": create_access_token(user_id),
        "refresh_token": _issue_refresh_token(user_id, db),
        "token_type": "bearer",
        "user": {"id": user_id, "email": email},
    }


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    row = db.execute(
        text("SELECT id::text, email, password_hash FROM users WHERE email = :email"),
        {"email": email},
    ).fetchone()

    if not row or not verify_password(body.password, row.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    ensure_demo_workspace_for_user(db, row.id)

    return {
        "access_token": create_access_token(row.id),
        "refresh_token": _issue_refresh_token(row.id, db),
        "token_type": "bearer",
        "user": {"id": row.id, "email": row.email},
    }


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(body.refresh_token)
    row = db.execute(
        text("""
            SELECT user_id::text, expires_at
            FROM refresh_tokens
            WHERE token_hash = :hash
        """),
        {"hash": token_hash},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.execute(
            text("DELETE FROM refresh_tokens WHERE token_hash = :hash"),
            {"hash": token_hash},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Rotate: delete old token, issue new pair
    db.execute(
        text("DELETE FROM refresh_tokens WHERE token_hash = :hash"),
        {"hash": token_hash},
    )
    ensure_demo_workspace_for_user(db, row.user_id)
    return {
        "access_token": create_access_token(row.user_id),
        "refresh_token": _issue_refresh_token(row.user_id, db),
        "token_type": "bearer",
    }