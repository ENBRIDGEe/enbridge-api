from typing import Annotated
import hashlib
import os
import secrets
from fastapi import Depends, HTTPException, status, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from sqlalchemy import text
from uuid import uuid4
from core.config import Settings
from core.database import SessionLocal
from fastapi.responses import JSONResponse
from schemas.schemas import Token, UserRegister

router = APIRouter()


def normalize_email(email: str) -> str:
    return email.strip().lower()


@lru_cache
def get_settings():
    return Settings()


password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

def verify_password(plain_password, hashed_password):
    """Verify plain text password against hashed password"""
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hash a plain text password"""
    return password_hash.hash(password)


# ============================================================================
# USER MANAGEMENT
# ============================================================================

def get_user(email: str):
    """Retrieve user from database by email"""
    email = normalize_email(email)
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                """
                SELECT id, name, email, password_hash, is_active, is_admin, 
                       refresh_token_hash, refresh_token_expires_at, created_at, updated_at
                FROM users
                WHERE LOWER(email) = :email
                """
            ),
            {"email": email},
        )
        user = result.mappings().first()
        return dict(user) if user else None
    finally:
        db.close()


def create_user(name: str, email: str, password_hash: str):
    """Create a new user in the database"""
    email = normalize_email(email)
    db = SessionLocal()
    try:
        existing_user = db.execute(
            text(
                """
                SELECT id, name, email, password_hash, is_active, is_admin, 
                       refresh_token_hash, refresh_token_expires_at, created_at, updated_at
                FROM users
                WHERE LOWER(email) = :email
                """
            ),
            {"email": email},
        ).mappings().first()

        if existing_user:
            return dict(existing_user), False

        new_user = db.execute(
            text(
                """
                INSERT INTO users (id, name, email, password_hash, is_active, is_admin, created_at, updated_at)
                VALUES (:id, :name, :email, :password_hash, TRUE, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, name, email, password_hash, is_active, is_admin, 
                          refresh_token_hash, refresh_token_expires_at, created_at, updated_at
                """
            ),
            {"id": str(uuid4()), "name": name, "email": email, "password_hash": password_hash},
        ).mappings().first()
        db.commit()
        return dict(new_user), True
    finally:
        db.close()


def authenticate_user(email: str, password: str):
    """Authenticate user by email and password"""
    email = normalize_email(email)
    user = get_user(email)
    if not user:
        return False
    hashed_password = user.get("password_hash")
    if not hashed_password or not verify_password(password, hashed_password):
        return False
    return user


# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

def create_access_token(settings, data: dict, expires_delta: timedelta | None = None, auth_method="password"):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire, "auth_method": auth_method})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    """Generate a random refresh token"""
    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str) -> str:
    """Hash a refresh token"""
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def store_refresh_token(user_id: str, refresh_token: str, settings: Settings):
    """Store refresh token hash in user table"""
    token_hash = hash_refresh_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE users
                SET refresh_token_hash = :token_hash,
                    refresh_token_expires_at = :expires_at,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
                """
            ),
            {
                "user_id": str(user_id),
                "token_hash": token_hash,
                "expires_at": expires_at,
            },
        )
        db.commit()
    finally:
        db.close()


def get_user_by_refresh_token(refresh_token: str):
    """Retrieve user by refresh token"""
    token_hash = hash_refresh_token(refresh_token)
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT id, name, email, password_hash, is_active, is_admin, 
                       refresh_token_hash, refresh_token_expires_at, created_at, updated_at
                FROM users
                WHERE refresh_token_hash = :token_hash
                    AND refresh_token_expires_at > CURRENT_TIMESTAMP
                    AND is_active = TRUE
                """
            ),
            {"token_hash": token_hash},
        ).mappings().first()
        return dict(row) if row else None
    finally:
        db.close()


def revoke_refresh_token(user_id: str):
    """Revoke refresh token by clearing it from user table"""
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE users
                SET refresh_token_hash = NULL,
                    refresh_token_expires_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        )
        db.commit()
    finally:
        db.close()


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register")
async def register(
    request: Request,
    user_data: UserRegister,
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Register a new user"""
    user_data.email = normalize_email(user_data.email)
    existing_user = get_user(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    password_hash = get_password_hash(user_data.password)
    user, created = create_user(user_data.name, user_data.email, password_hash)

    if not created:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create tokens
    access_token = create_access_token(
        settings,
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        auth_method="password",
    )
    refresh_token = create_refresh_token()
    store_refresh_token(user["id"], refresh_token, settings)

    return JSONResponse(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "auth_method": "password",
        }
    )


@router.post("/token")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Login with email and password"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = create_access_token(
        settings,
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        auth_method="password",
    )
    refresh_token = create_refresh_token()
    store_refresh_token(user["id"], refresh_token, settings)

    return JSONResponse(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "auth_method": "password",
        }
    )


@router.post("/auth/refresh")
async def refresh_access_token(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Refresh access token using refresh token"""
    # Get refresh token from request body (for cross-domain requests)
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
    except:
        refresh_token = None

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )

    token_user = get_user_by_refresh_token(refresh_token)
    if not token_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Create new access token
    access_token = create_access_token(
        settings,
        data={"sub": token_user["email"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        auth_method="refresh",
    )

    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "auth_method": "refresh",
        }
    )


@router.post("/logout")
async def logout(
    current_user_data: Annotated[dict, Depends(lambda: {"user": None})],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Logout user"""
    # Get user from Authorization header
    try:
        # This is a simple logout - just return success
        # The frontend will clear tokens from localStorage
        return JSONResponse({"message": "Logged out successfully"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        )


# ============================================================================
# AUTHORIZATION
# ============================================================================

async def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
):
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Token comes from Authorization header (oauth2_scheme)
        if not token:
            raise credentials_exception

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        auth_method = payload.get("auth_method", "password")

        if username is None:
            raise credentials_exception

        user = get_user(username)
        if user is None:
            raise credentials_exception

        return {"user": user, "auth_method": auth_method}

    except InvalidTokenError:
        raise credentials_exception


async def get_current_active_user(
    current_user_data: Annotated[dict, Depends(get_current_user)],
):
    """Verify user is active"""
    user = current_user_data["user"]
    auth_method = current_user_data["auth_method"]

    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")

    return {"user": user, "auth_method": auth_method}
