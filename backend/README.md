# Enbridge Backend API — Frontend Integration Guide

This document summarizes the API surface (paths, request/response shapes, auth) based on the server OpenAPI schema so frontend engineers can integrate the client.

Base URL (local dev):

```text
http://127.0.0.1:8000
```

Interactive docs / OpenAPI:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/openapi.json
```

Quick start (dev):

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Environment (backend/.env)

- The app reads lowercase DB parts: `user`, `password`, `host`, `port`, `dbname`. If all present the app builds the Postgres `DATABASE_URL`. Otherwise it falls back to `sqlite:///./enbridge.db`.
- Required for production: `SECRET_KEY`, DB credentials, Google OAuth keys (if using Google sign-in).

Example `.env` (fill password and hosts):

```env
SECRET_KEY=change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

user=postgres
password=your-db-password
host=your-db-host
port=5432
dbname=postgres

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
```

Authentication

- All protected endpoints require an Authorization header:

```http
Authorization: Bearer <access_token>
```

Main endpoints (summary and frontend usage)

- POST `/register` — Register a new user (JSON body: `UserRegister`)
    - Body schema: `UserRegister` { name, email, password }
    - Response: `Token` { access_token, token_type }

- POST `/token` — Login (OAuth2 password form)
    - Content-Type: `application/x-www-form-urlencoded`
    - Fields: `username` (email), `password`
    - Response: `Token`

- GET `/auth/google` — Redirect to Google for OAuth sign-in.
- GET `/auth/google/callback` — Google callback: returns `Token` + user info on success.

- GET `/users/me/` — Get current user (requires auth)
- GET `/users/me/public` — Public profile of current user (no auth required)
- GET `/users/debug` — Debug helper (dev only)
- GET `/users/auth` — Auth check (requires auth)

- Goals
    - GET `/goals` — List goals for current user (requires auth)
    - POST `/goals` — Create a goal (body: `GoalCreate`)
        - `GoalCreate`: { title, category, deadline (date-time), status }
    - GET `/goals/{goal_id}` — Read a specific goal (requires auth)
    - PATCH `/goals/{goal_id}` — Update a goal (body: `GoalUpdate`)
    - DELETE `/goals/{goal_id}` — Delete goal

- Milestones
    - POST `/milestones` — Create milestone (body: `MilestoneCreate`)
        - `MilestoneCreate`: { goal_id (uuid), target_date (date-time), order_index (integer) }
    - GET `/milestones/goal/{goal_id}` — List milestones for a goal (requires auth)

- Tasks
    - GET `/tasks` — List tasks for current user (requires auth)
    - POST `/tasks` — Create task (body: `TaskCreate`)
        - `TaskCreate`: { milestone_id (uuid), due_date (date-time), completed (bool) }
    - PATCH `/tasks/{task_id}` — Update task (body: `TaskUpdate`)
    - DELETE `/tasks/{task_id}` — Delete task

- Notifications
    - GET `/notifications/settings` — Read notification settings for current user (requires auth)
    - PATCH `/notifications/settings` — Update settings (body: `NotificationUpdate`)
        - `NotificationUpdate`: { push_enabled (bool), remainder (date-time) }

Request/response examples

- Register example

```bash
curl -X POST http://127.0.0.1:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alex","email":"alex@example.com","password":"secret"}'
```

Response (200):

```json
{
	"access_token": "<jwt>",
	"token_type": "bearer"
}
```

- Login example (form encoded)

```bash
curl -X POST http://127.0.0.1:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alex@example.com&password=secret"
```

Frontend integration notes

- Use the OpenAPI JSON at `/openapi.json` to generate typed clients (e.g., TypeScript via openapi-generator or `openapi-typescript`).
- For auth flows, persist `access_token` securely (httpOnly cookie or in-memory) and attach `Authorization: Bearer <token>` for protected requests.
- Google OAuth: call `/auth/google` from the browser (redirect) and handle the callback at `/auth/google/callback` — the server responds with the JWT.
- Errors: validation errors return 422 with `HTTPValidationError` shape; missing DB returns 503 with a helpful message.

Database & migrations

- The app will attempt to create tables at startup when the DB is available. For production use, prefer Alembic migrations instead of relying on `create_all()`.
- Recommended workflow:

```bash
# set DATABASE env (.env)
cd backend
source .venv/bin/activate
# create migration
alembic revision --autogenerate -m "init"
alembic upgrade head
```

Where to look for full schema

- The OpenAPI JSON at `/openapi.json` contains the components/schemas referenced above (UserRegister, Token, GoalCreate, GoalUpdate, MilestoneCreate, TaskCreate, TaskUpdate, NotificationUpdate). Use that file to produce client types.

If you want, I can generate a small `openapi-typescript` client example and a short usage snippet for the frontend. Would you like that?
