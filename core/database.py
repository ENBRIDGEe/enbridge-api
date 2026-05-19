from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from core.config import Settings

settings = Settings()

DATABASE_URL = settings.DATABASE_URL

# Configure engine arguments based on database type
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL-specific pool configuration
    from sqlalchemy.pool import QueuePool
    engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600
    })

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, **engine_kwargs)

# Test the connection
try:
    with engine.connect() as connection:
        print(f"Connection successful to {DATABASE_URL.split(':')[0]}!")
except Exception as e:
    print(f"Failed to connect: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)