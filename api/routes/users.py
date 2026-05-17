from typing import Annotated
from fastapi import Depends, APIRouter, Request
import os
from sqlalchemy import text
from core.database import SessionLocal

from .auth import get_current_active_user

router = APIRouter()


def get_all_users():
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT id, name, email, is_active, is_admin, created_at, updated_at FROM users")
        )
        return [dict(user) for user in result.mappings().all()]
    finally:
        db.close()


# Endpoint to get items belonging to current authenticated user
# Returns a list containing a sample item with the user's username
@router.get("/users/me/")
async def read_own_items(
    current_user: Annotated[dict, Depends(get_current_active_user)]
):
    users = get_all_users()
    return {"users": users}




@router.get("/users/me/public")
async def read_own_items():
    users = get_all_users()
    return {"users": users}


@router.get("/users/debug")
async def debug_users_table():
    db = SessionLocal()
    try:
        database = db.execute(text("SELECT current_database()")).scalar()
        schema = db.execute(text("SELECT current_schema()")).scalar()
        count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        latest_users = db.execute(
            text("SELECT id, name, email, is_active, created_at FROM users ORDER BY created_at DESC LIMIT 5")
        ).mappings().all()

        return {
            "database": database,
            "schema": schema,
            "users_count": count,
            "latest_users": [dict(user) for user in latest_users],
        }
    finally:
        db.close()


@router.get("/users/auth")
async def read_own_items(
    current_user_data: Annotated[dict, Depends(get_current_active_user)]
):
    user = current_user_data["user"]
    auth_method = current_user_data["auth_method"]

    return {
        "message": f"Authenticated via {auth_method}",
        "user": user
    }


# Dev debug endpoint: inspect session and cookie for troubleshooting
@router.get("/debug/auth-cookie")
async def debug_auth_cookie(request: Request):
    # Return cookie, header and session info (development only)
    cookie_name = os.getenv("ACCESS_COOKIE_NAME", "access_token")
    cookie_value = request.cookies.get(cookie_name)
    try:
        session_keys = list(request.session.keys())
    except Exception:
        session_keys = None

    # Return a subset of headers relevant for CORS/cookie issues
    headers_of_interest = {
        "origin": request.headers.get("origin"),
        "referer": request.headers.get("referer"),
        "cookie": request.headers.get("cookie"),
        "authorization": request.headers.get("authorization"),
    }

    return {
        "cookie_name": cookie_name,
        "cookie_present": bool(cookie_value),
        "cookie_value_sample": (cookie_value[:16] + "...") if cookie_value else None,
        "session_keys": session_keys,
        "headers": headers_of_interest,
    }
