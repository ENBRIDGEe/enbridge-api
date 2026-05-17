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
from fastapi.responses import JSONResponse, RedirectResponse, Response
from schemas.schemas import Token, UserRegister

router = APIRouter()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_frontend_redirect_url(settings: Settings) -> str:
    return settings.FRONTEND_URL or "http://localhost:5173/app/dashboard"


def get_cookie_samesite(settings: Settings) -> str:
    same_site = (settings.COOKIE_SAMESITE or "lax").lower().strip()
    if same_site not in {"lax", "strict", "none"}:
        return "lax"
    return same_site


def should_use_secure_cookie(request: Request, settings: Settings) -> bool:
    return request.url.scheme == "https" or str(settings.COOKIE_SECURE).lower() == "true"


def get_access_cookie_name(settings: Settings | None = None) -> str:
    return (settings.ACCESS_COOKIE_NAME if settings else "access_token") or "access_token"


def get_refresh_cookie_name(settings: Settings | None = None) -> str:
    return (settings.REFRESH_COOKIE_NAME if settings else "refresh_token") or "refresh_token"


@lru_cache
def get_settings():
    return Settings()

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Verifies if a plain text password matches a hashed password
# Returns True if passwords match, False otherwise
def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)

# Generates a hashed version of a plain text password
# Returns the hashed password string
def get_password_hash(password):
    return password_hash.hash(password)

# Retrieves a user from the database by username
# Returns a UsrInDB object if found, None otherwise
def get_user(email: str):
    email = normalize_email(email)
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                """
                SELECT id, name, email, password_hash, is_active, is_admin, created_at, updated_at
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


# Creates a user row that matches the users schema
def create_user(name: str, email: str, password_hash: str):
    email = normalize_email(email)
    db = SessionLocal()
    try:
        existing_user = db.execute(
            text(
                """
                SELECT id, name, email, password_hash, is_active, is_admin, created_at, updated_at
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
                RETURNING id, name, email, password_hash, is_active, is_admin, created_at, updated_at
                """
            ),
            {"id": str(uuid4()), "name": name, "email": email, "password_hash": password_hash},
        ).mappings().first()
        db.commit()
        return dict(new_user), True
    finally:
        db.close()


# Authenticates a user by verifying username and password
# Returns the user object if authentication successful, False otherwise
def authenticate_user(email: str, password: str):
    email = normalize_email(email)
    user = get_user(email)
    if not user:
        return False
    hashed_password = user.get("password_hash")
    if not hashed_password or not verify_password(password, hashed_password):
        return False
    return user

# this function is used to create access token
# it takes in settings, data, expires_delta and auth_method as arguments
# returns the encoded jwt token
def create_access_token(settings, data: dict, expires_delta: timedelta | None = None, auth_method="password"):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    to_encode.update({"exp": expire, "auth_method": auth_method})  # Include auth method
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def store_refresh_token(user_id, refresh_token: str, settings: Settings):
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
                    refresh_token_revoked_at = NULL,
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


def get_refresh_token_user(refresh_token: str):
    token_hash = hash_refresh_token(refresh_token)
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT id, name, email, password_hash, is_active, is_admin, created_at, updated_at
                FROM users
                WHERE refresh_token_hash = :token_hash
                  AND refresh_token_revoked_at IS NULL
                  AND refresh_token_expires_at > CURRENT_TIMESTAMP
                  AND is_active = TRUE
                """
            ),
            {"token_hash": token_hash},
        ).mappings().first()
        return dict(row) if row else None
    finally:
        db.close()


def revoke_refresh_token(refresh_token: str):
    token_hash = hash_refresh_token(refresh_token)
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                UPDATE users
                SET refresh_token_revoked_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE refresh_token_hash = :token_hash
                  AND refresh_token_revoked_at IS NULL
                """
            ),
            {"token_hash": token_hash},
        )
        db.commit()
    finally:
        db.close()


def set_auth_cookies(
    response: Response,
    request: Request,
    settings: Settings,
    access_token: str,
    refresh_token: str | None = None,
):
    cookie_domain = settings.COOKIE_DOMAIN
    response.set_cookie(
        key=get_access_cookie_name(settings),
        value=access_token,
        httponly=True,
        secure=should_use_secure_cookie(request, settings),
        samesite=get_cookie_samesite(settings),
        max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        path="/",
        domain=cookie_domain,
    )

    if refresh_token:
        refresh_max_age = int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
        response.set_cookie(
            key=get_refresh_cookie_name(settings),
            value=refresh_token,
            httponly=True,
            secure=should_use_secure_cookie(request, settings),
            samesite=get_cookie_samesite(settings),
            max_age=refresh_max_age,
            path="/",
            domain=cookie_domain,
        )


def clear_auth_cookies(response: Response, settings: Settings):
    cookie_domain = settings.COOKIE_DOMAIN
    for cookie_name in (get_access_cookie_name(settings), get_refresh_cookie_name(settings)):
        response.delete_cookie(
            key=cookie_name,
            path="/",
            domain=cookie_domain,
            samesite=get_cookie_samesite(settings),
        )


def create_user_session(request: Request, user: dict, settings: Settings, auth_method: str, redirect: bool = True):
    access_token = create_access_token(
        settings,
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        auth_method=auth_method,
    )
    refresh_token = create_refresh_token()
    store_refresh_token(user["id"], refresh_token, settings)

    if redirect:
        response = RedirectResponse(url=get_frontend_redirect_url(settings))
    else:
        response = JSONResponse(
            {
                "access_token": access_token,
                "token_type": "bearer",
                "auth_method": auth_method,
            }
        )

    set_auth_cookies(response, request, settings, access_token, refresh_token)
    return response

# Verifies the token and returns the user and auth method
async def get_current_user(settings: Annotated[Settings, Depends(get_settings)], request: Request, token: Annotated[str | None, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # If no Authorization header token, fall back to HttpOnly cookie
        if not token:
            cookie_name = get_access_cookie_name(settings)
            token = request.cookies.get(cookie_name)

        if not token:
            raise credentials_exception

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        auth_method = payload.get("auth_method", "password")  # Default to password auth

        if username is None:
            raise credentials_exception

        user = get_user(username)
        if user is None:
            raise credentials_exception

        return {"user": user, "auth_method": auth_method}  # Return user and auth method

    except InvalidTokenError:
        raise credentials_exception

# Verifies if a user is active (not disabled)
# Raises HTTPException if user is disabled, otherwise returns the user
async def get_current_active_user(
    current_user_data: Annotated[dict, Depends(get_current_user)]
):
    user = current_user_data["user"]
    auth_method = current_user_data["auth_method"]

    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Inactive user")

    return {"user": user, "auth_method": auth_method}


# Endpoint for user registration
# Stores the user's credentials in the users table and returns a JWT token
@router.post("/register")
async def register(
    request: Request,
    user_data: UserRegister,
    settings: Annotated[Settings, Depends(get_settings)],
):
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

    return create_user_session(request, user, settings, auth_method="password", redirect=False)


# Endpoint for user authentication and token generation
# Validates username/password, sets the JWT cookie, and redirects on success
@router.post("/token")
async def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
):
    user = authenticate_user( form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_user_session(request, user, settings, auth_method="password")


@router.post("/auth/refresh")
async def refresh_access_token(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    refresh_token = request.cookies.get(get_refresh_cookie_name(settings))
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    token_user = get_refresh_token_user(refresh_token)
    if not token_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    access_token = create_access_token(
        settings,
        data={"sub": token_user["email"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        auth_method="refresh",
    )

    response = JSONResponse({"message": "Access token refreshed"})
    set_auth_cookies(response, request, settings, access_token, refresh_token)
    return response


@router.post("/logout")
async def logout(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    refresh_token = request.cookies.get(get_refresh_cookie_name(settings))
    if refresh_token:
        revoke_refresh_token(refresh_token)

    response = JSONResponse({"message": "Logged out"})
    clear_auth_cookies(response, settings)
    return response
