from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from core.database import engine
from core.config import Settings
from api.routes import auth, goals, google_auth, milestones, notifications, tasks, users

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
settings = Settings()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Database unavailable. Check DATABASE_URL and ensure PostgreSQL is running."},
    )


# Include routers
app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(users.router)
app.include_router(goals.router)
app.include_router(milestones.router)
app.include_router(tasks.router)
app.include_router(notifications.router)


@app.get("/")
def home():
    return{"message": "Welcome to Enbridge API!"}
