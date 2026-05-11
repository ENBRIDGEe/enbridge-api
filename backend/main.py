from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from api import admin_router
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(admin_router)