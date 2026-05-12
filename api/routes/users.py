from typing import Annotated
from fastapi import Depends, APIRouter
from sqlalchemy import text
from core.database import SessionLocal

from .auth import get_current_active_user

router = APIRouter()


def get_all_users():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT * FROM users"))
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
