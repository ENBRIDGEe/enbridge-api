from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Users
from ..deps import get_db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_db)],
    responses={404: {"description": "Not found"}},
)

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(Users).all()
    return users
    db.commit()