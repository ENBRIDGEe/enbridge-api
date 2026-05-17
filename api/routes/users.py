from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from core.database import SessionLocal
from .auth import get_current_active_user
from schemas.schemas import UserOut, UserPublic, UserUpdate

router = APIRouter()


@router.get("/users/me/", response_model=UserOut, tags=["users"])
@router.get("/users/me", response_model=UserOut, tags=["users"])
async def read_current_user(
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    """
    Get the full profile of the currently authenticated user.
    """
    return current_user_data["user"]


@router.get("/users/me/public", response_model=UserPublic, tags=["users"])
async def read_current_user_public(
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    """
    Get the safe public profile info of the currently authenticated user.
    """
    return current_user_data["user"]


@router.patch("/users/me", response_model=UserOut, tags=["users"])
async def update_current_user(
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
    user_update: UserUpdate,
):
    """
    Update the profile of the currently authenticated user.
    """
    user = current_user_data["user"]
    new_name = user_update.name
    if not new_name:
        return user

    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE users SET name = :name, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"name": new_name, "id": user["id"]},
        )
        db.commit()
        user["name"] = new_name
        return user
    finally:
        db.close()


@router.get("/users/auth", tags=["users"], include_in_schema=False)
async def read_current_user_auth(
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    # Keep as a non-public helper endpoint; do not expose raw user/session internals.
    user = current_user_data.get("user") or {}
    return {
        "auth_method": current_user_data.get("auth_method"),
        "user": {
            "id": user.get("id"),
            "name": user.get("name"),
        },
    }
