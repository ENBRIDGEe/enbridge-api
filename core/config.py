from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173/app/dashboard")
    CORS_ALLOW_ORIGINS: str = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:5173",
    )
    # Cookie settings
    ACCESS_COOKIE_NAME: str = os.getenv("ACCESS_COOKIE_NAME", "access_token")
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")
    COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN") or None

    # Prefer explicit DATABASE_URL when provided.
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")

    # Fetch variables (optional fallback when DATABASE_URL is not set)
    # Lowercase env var names for Postgres: user/password/host/port/dbname.
    USER: str | None = os.getenv("user")
    PASSWORD: str | None = os.getenv("password")
    HOST: str | None = os.getenv("host")
    PORT: str | None = os.getenv("port")
    DBNAME: str | None = os.getenv("dbname")

    # Construct the SQLAlchemy connection string.
    # Priority: explicit DATABASE_URL -> Postgres parts -> sqlite fallback.
    if not DATABASE_URL:
        if USER and PASSWORD and HOST and PORT and DBNAME:
            DATABASE_URL = (
                f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
            )
        else:
            DATABASE_URL = "sqlite:///./enbridge.db"

    # Lambda filesystems are read-only except /tmp.
    # If a relative sqlite path is used in Lambda, switch to /tmp automatically.
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME") and DATABASE_URL == "sqlite:///./enbridge.db":
        DATABASE_URL = "sqlite:////tmp/enbridge.db"
