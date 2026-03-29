from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.utils import decode_access_token
from app.db import SessionLocal

bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """
    FastAPI dependency — validates Bearer JWT.
    Add Depends(get_current_user) to any router to require authentication.
    """
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.execute(
        text("SELECT id::text, email, full_name FROM users WHERE id = CAST(:uid AS UUID)"),
        {"uid": user_id},
    ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return dict(user._mapping)