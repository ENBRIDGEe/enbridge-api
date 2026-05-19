# Enbridge Backend API

This repository contains the backend for Enbridge: a FastAPI service with cookie-based auth, SQLite by default, and optional PostgreSQL support when the lowercase database variables are provided.

The OpenAPI schema is the source of truth for request and response shapes. Use this README as a practical integration guide for local development and frontend wiring.

## Quick Start

### Local server

```bash
cd /home/sam/Repositories/enbridge-api
source .venv/bin/activate
pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### OpenAPI docs

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
```

### Database behavior

- If `user`, `password`, `host`, `port`, and `dbname` are present in `.env`, the app builds a PostgreSQL `DATABASE_URL`.
- Otherwise it falls back to `sqlite:///./enbridge.db`.
- That means the repository works locally without any external database, which is the default path for development.

### Example `.env`

```env
SECRET_KEY=change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Optional: PostgreSQL. If omitted, the app uses sqlite:///./enbridge.db.
user=postgres
password=your-db-password
host=your-db-host
port=5432
dbname=postgres

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173/app/dashboard
CORS_ALLOW_ORIGINS=http://localhost:5173
ACCESS_COOKIE_NAME=access_token
REFRESH_COOKIE_NAME=refresh_token
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

## Authentication

The API supports two client-facing auth paths:

- Authorization header: `Authorization: Bearer <access_token>`
- HttpOnly cookies set by login, refresh, or Google OAuth flows

For browser requests, send credentials so cookies are included:

```js
fetch("http://localhost:8000/goals", {
  credentials: "include",
});
```

The access JWT also includes an `auth_method` claim, which can be `password`, `google`, or `refresh`.

### Auth flow summary

- `POST /register` creates a user and returns a token payload.
- `POST /token` logs in with form data and sets auth cookies.
- `GET /auth/google` starts Google OAuth.
- `GET /auth/google/callback` finishes Google OAuth, sets cookies, and redirects to `FRONTEND_URL`.
- `POST /auth/refresh` reissues the access cookie using the refresh cookie.
- `POST /logout` revokes the refresh token and clears cookies.

### Refresh token behavior

Refresh tokens are stored in the `refresh_tokens` table. Login writes a new row, refresh validates the active row, and logout revokes it. The refresh cookie is reused until logout or expiry.

Example refresh request:

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  --cookie "refresh_token=<current_refresh_token>" \
  -i
```

## API Overview

### Users

- `GET /users/me` returns the authenticated user.
- `PATCH /users/me` updates the user's name.
- `GET /users/me/public` returns safe public fields.
- `GET /users/auth` is a hidden helper for frontend auth checks and returns `{ auth_method, user: { id, name } }`.

### Goals

- `GET /goals` lists the current user's goals.
- `POST /goals` creates a goal.
- `GET /goals/{goal_id}` reads one goal.
- `PATCH /goals/{goal_id}` updates one goal.
- `DELETE /goals/{goal_id}` deletes one goal.
- `POST /goals/{goal_id}/activity` records activity for a day.
- `GET /goals/{goal_id}/activity` lists activity days.
- `DELETE /goals/{goal_id}/activity` removes activity for a day.

Goal create payload:

```json
{
  "title": "Finish onboarding",
  "description": "Ship the onboarding flow",
  "category": "product",
  "target_date": "2026-05-31T00:00:00Z",
  "deadline": "2026-05-31T00:00:00Z",
  "status": "active",
  "progress_percentage": 0
}
```

### Milestones

- `POST /milestones` creates a milestone.
- `GET /milestones/goal/{goal_id}` lists milestones for one goal.

### Tasks

- `GET /tasks` lists tasks for the current user.
- `POST /tasks` creates a task.
- `PATCH /tasks/{task_id}` updates a task.
- `DELETE /tasks/{task_id}` deletes a task.

Task create payload:

```json
{
  "title": "Write release notes",
  "milestone_id": null,
  "due_date": "2026-05-24T09:00:00Z",
  "completed": false
}
```

### Notifications

- `GET /notifications/settings` reads the current user's notification settings.
- `PATCH /notifications/settings` updates them.

The update payload supports the backward-compatible alias `remainder` for `reminder_time`, and `reminder_time` accepts either a time or a datetime value.

```json
{
  "push_enabled": true,
  "email_enabled": true,
  "reminder_time": "09:00:00",
  "timezone": "UTC"
}
```

### Analytics

- `POST /analytics/focus-sessions` records a completed focus session.
- `GET /analytics/focus-time` returns aggregated focus time for a date range.

Focus session payload:

```json
{
  "session_duration_minutes": 25,
  "completed_at": "2026-05-16T22:45:00Z",
  "date": "2026-05-16"
}
```

## Response Shapes

The most commonly used response types are:

- `Token`: `{ access_token, token_type, auth_method }`
- `UserOut`: `{ id, name, email, is_active, is_admin, created_at, updated_at }`
- `UserPublic`: `{ id, name }`
- `FocusTimeResponse`: `{ date, total_minutes, sessions_count, avg_session_minutes, focus_time_display }`

## Frontend Notes

- Keep the frontend on `http://localhost:5173` and the API on `http://localhost:8000` during local development.
- Set `CORS_ALLOW_ORIGINS` to the frontend origin when using cookie-based auth.
- Use `GET /users/auth` for lightweight dashboard bootstrapping.
- If login redirects correctly but the dashboard keeps spinning, the issue is usually in the frontend auth guard or data loading path.

## Testing

```bash
pytest -q
```

Before running tests, point `.env` at a safe database. The suite creates and mutates real data.

## Migrations

SyncSchema changes are managed with Alembic.

```bash
source .venv/bin/activate
alembic current
alembic revision --autogenerate -m "update models"
alembic upgrade head
alembic check
```

If you use the sqlite default locally, `alembic upgrade head` will create and update `enbridge.db` as needed.

Where to look for full schema

- The OpenAPI JSON at `/openapi.json` contains the components/schemas referenced above (UserRegister, Token, GoalCreate, GoalUpdate, MilestoneCreate, TaskCreate, TaskUpdate, NotificationUpdate). Use that file to produce client types.
