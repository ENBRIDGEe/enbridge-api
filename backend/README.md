# Enbridge Goal Execution Platform - Backend MVP

A production-quality backend API for Enbridge, a goal execution platform built with FastAPI, SQLAlchemy, and PostgreSQL.

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL 12+
- pip

### Installation

1. **Clone and navigate to backend:**

    ```bash
    cd backend
    ```

2. **Create and activate virtual environment:**

    ```bash
    python3.13 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables:**

    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```

5. **Create PostgreSQL database:**

    ```bash
    createdb enbridge
    ```

6. **Start development server:**
    ```bash
    uvicorn app.main:app --reload
    ```

The API will be available at `http://localhost:8000`

### API Documentation

- **Interactive Docs (Swagger):** http://localhost:8000/docs
- **Alternative Docs (ReDoc):** http://localhost:8000/redoc

## Project Structure

```
app/
├── main.py                 # FastAPI app entry point
├── api/
│   ├── deps.py            # Dependency injections (auth, db)
│   └── routes/
│       ├── auth.py        # Authentication endpoints
│       ├── users.py       # User profile endpoints
│       ├── goals.py       # Goal CRUD endpoints
│       ├── milestones.py  # Milestone CRUD endpoints
│       ├── tasks.py       # Task CRUD endpoints
│       ├── progress.py    # Progress tracking endpoints
│       └── notifications.py # Notification settings endpoints
├── core/
│   ├── config.py          # Pydantic settings
│   ├── database.py        # SQLAlchemy setup
│   ├── security.py        # JWT & password hashing
│   └── exceptions.py      # Custom HTTP exceptions
├── models/
│   ├── user.py
│   ├── goal.py
│   ├── milestone.py
│   ├── task.py
│   ├── progress_log.py
│   └── notification_setting.py
├── schemas/
│   ├── auth.py
│   ├── user.py
│   ├── goal.py
│   ├── milestone.py
│   ├── task.py
│   ├── progress.py
│   └── notification.py
├── repositories/
│   ├── user_repository.py
│   ├── goal_repository.py
│   ├── milestone_repository.py
│   ├── task_repository.py
│   ├── progress_repository.py
│   └── notification_repository.py
└── services/
    ├── auth_service.py
    ├── user_service.py
    ├── goal_service.py
    ├── milestone_service.py
    ├── task_service.py
    ├── progress_service.py
    └── notification_service.py
```

## API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user (requires Bearer token)

### Users

- `GET /api/v1/users/me` - Get current user profile
- `PATCH /api/v1/users/me` - Update current user profile

### Goals

- `POST /api/v1/goals` - Create goal
- `GET /api/v1/goals` - List all user goals
- `GET /api/v1/goals/{goal_id}` - Get specific goal
- `PATCH /api/v1/goals/{goal_id}` - Update goal
- `DELETE /api/v1/goals/{goal_id}` - Delete goal

### Milestones

- `POST /api/v1/milestones?goal_id=<goal_id>` - Create milestone
- `GET /api/v1/milestones/goal/{goal_id}` - List goal milestones
- `GET /api/v1/milestones/{milestone_id}` - Get milestone
- `PATCH /api/v1/milestones/{milestone_id}` - Update milestone
- `DELETE /api/v1/milestones/{milestone_id}` - Delete milestone

### Tasks

- `POST /api/v1/tasks?milestone_id=<milestone_id>` - Create task
- `GET /api/v1/tasks/milestone/{milestone_id}` - List milestone tasks
- `GET /api/v1/tasks/{task_id}` - Get task
- `PATCH /api/v1/tasks/{task_id}` - Update task
- `PATCH /api/v1/tasks/{task_id}/complete` - Mark task complete
- `PATCH /api/v1/tasks/{task_id}/uncomplete` - Mark task incomplete
- `DELETE /api/v1/tasks/{task_id}` - Delete task

### Progress

- `GET /api/v1/progress/summary` - Get progress summary
- `GET /api/v1/progress/goals/{goal_id}` - Get goal progress logs

### Notifications

- `GET /api/v1/notifications/settings` - Get notification settings
- `PATCH /api/v1/notifications/settings` - Update notification settings

## Authentication

All endpoints (except registration and login) require a Bearer token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <your_access_token>" http://localhost:8000/api/v1/users/me
```

## Environment Variables

- `APP_NAME` - Application name (default: "Enbridge")
- `DEBUG` - Enable debug mode (default: False)
- `SECRET_KEY` - JWT secret key (required in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiry (default: 60)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiry (default: 30)
- `DATABASE_URL` - PostgreSQL connection string
- `ALGORITHM` - JWT algorithm (default: HS256)

## Database Migrations

Alembic is configured for database migrations. (Currently using SQLAlchemy Core schema creation on startup.)

## Testing

Run pytest tests:

```bash
pytest
```

## Architecture

The backend follows a layered architecture:

1. **Routes** - Define endpoints, validate requests, call services
2. **Dependencies** - Provide DB session and authenticated user
3. **Services** - Business logic, authorization, transaction management
4. **Repositories** - Database CRUD operations
5. **Models** - SQLAlchemy ORM models
6. **Schemas** - Pydantic request/response validation

## Technology Stack

- **Framework:** FastAPI 0.115+
- **ORM:** SQLAlchemy 2.0
- **Database:** PostgreSQL with psycopg
- **Validation:** Pydantic v2
- **Authentication:** JWT (python-jose) + bcrypt
- **Testing:** pytest
- **API Server:** Uvicorn

## Notes

- All endpoints require authentication except `/api/v1/auth/register`, `/api/v1/auth/login`, and `/api/v1/health`
- User ownership is enforced at the service layer
- Timestamps use UTC
- UUIDs are used as primary keys
