from typing import Annotated
import os
from fastapi import Depends, HTTPException, status, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel
from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from sqlalchemy import text
from uuid import uuid4
from core.config import Settings
from core.database import SessionLocal
from fastapi.responses import RedirectResponse

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str


class UserRegister(BaseModel):
    name: str
    email: str
    password: str


def get_frontend_redirect_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173/app/dashboard")


def get_cookie_samesite() -> str:
    same_site = os.getenv("COOKIE_SAMESITE", "lax").lower().strip()
    if same_site not in {"lax", "strict", "none"}:
        return "lax"
    return same_site


def should_use_secure_cookie(request: Request) -> bool:
    return request.url.scheme == "https" or os.getenv("COOKIE_SECURE", "false").lower() == "true"


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
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
        user = result.mappings().first()
        return dict(user) if user else None
    finally:
        db.close()


# Creates a user row that matches the users schema
def create_user(name: str, email: str, password_hash: str):
    db = SessionLocal()
    try:
        existing_user = db.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": email},
        ).mappings().first()

        if existing_user:
            return dict(existing_user), False

        new_user = db.execute(
            text(
                """
                INSERT INTO users (id, name, email, password_hash, is_active, is_admin, created_at, updated_at)
                VALUES (:id, :name, :email, :password_hash, TRUE, FALSE, NOW(), NOW())
                RETURNING *
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
    user = get_user(email)
    if not user:
        return False
    hashed_password = user.get("hashed_password") or user.get("password_hash")
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
            cookie_name = os.getenv("ACCESS_COOKIE_NAME", "access_token")
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
async def register(user_data: UserRegister, settings: Annotated[Settings, Depends(get_settings)]) -> Token:
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

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        settings, data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


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
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        settings, data={"sub": user['email']}, expires_delta=access_token_expires
    )

    cookie_name = os.getenv("ACCESS_COOKIE_NAME", "access_token")
    max_age = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    cookie_domain = os.getenv("COOKIE_DOMAIN") or None

    response = RedirectResponse(url=get_frontend_redirect_url())
    response.set_cookie(
        key=cookie_name,
        value=access_token,
        httponly=True,
        secure=should_use_secure_cookie(request),
        samesite=get_cookie_samesite(),
        max_age=max_age,
        expires=max_age,
        path="/",
        domain=cookie_domain,
    )
    return response
