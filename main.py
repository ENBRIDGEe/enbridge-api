from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from core.database import engine

from core.config import Settings
from models.models import Base, Focus_sessions
from api.routes import auth, analytics, goals, google_auth, milestones, notifications, tasks, users

app = FastAPI()
settings = Settings()


@app.on_event("startup")
def ensure_sqlite_schema() -> None:
    # In sqlite deployments (including serverless /tmp), create schema if it does not exist.
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

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

@app.middleware("http")
async def debug_token_middleware(request: Request, call_next):
    if request.url.path == "/token" and request.method == "POST":
        print("====== INCOMING /token REQUEST ======")
        print("Headers:", dict(request.headers))
        try:
            body = await request.body()
            print("Raw Body:", body)
        except Exception as e:
            print("Could not read body:", e)
        print("=====================================")
    response = await call_next(request)
    return response

@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Check DATABASE_URL and ensure the configured database is reachable and migrated."},
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
