from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from core.database import engine

from core.config import Settings
from models.models import Base, Focus_sessions
from api.routes import auth, analytics, goals, google_auth, milestones, notifications, tasks, users

from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
settings = Settings()

cors_allow_origins = [
    origin.strip()
    for origin in settings.CORS_ALLOW_ORIGINS.split(",")
    if origin.strip()
]
if not cors_allow_origins:
    cors_allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure session cookie options to match auth cookie behavior so OAuth state is preserved
session_https_only = bool(settings.COOKIE_SECURE)
session_same_site = settings.COOKIE_SAMESITE if settings.COOKIE_SAMESITE in {"lax", "strict", "none"} else "lax"
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=session_https_only,
    same_site=session_same_site,
)

@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Check DATABASE_URL and ensure PostgreSQL is running."},
    )


# Include routers
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(google_auth.router)
app.include_router(users.router)
app.include_router(goals.router)
app.include_router(milestones.router)
app.include_router(tasks.router)
app.include_router(notifications.router)


@app.get("/")
def home():
    return{"message": "Welcome to Enbridge API!"}
