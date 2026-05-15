# Enbridge Backend API — Frontend Integration Guide

This document summarizes the API surface (paths, request/response shapes, auth) based on the server OpenAPI schema so frontend engineers can integrate the client.

Base URL (local dev):

```text
http://localhost:8000
```

Interactive docs / OpenAPI:

```text
http://localhost:8000/docs
http://localhost:8000/openapi.json
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
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
CORS_ALLOW_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173/app/dashboard
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

Authentication

- Protected endpoints accept either an Authorization header or the HttpOnly JWT cookie set by the browser OAuth flow:

```http
Authorization: Bearer <access_token>
```

When using the cookie, send browser requests with credentials enabled.

Main endpoints (summary and frontend usage)

- POST `/register` — Register a new user (JSON body: `UserRegister`)
    - Body schema: `UserRegister` { name, email, password }
    - Response: `Token` { access_token, token_type }

- POST `/token` — Login (OAuth2 password form)
    - Content-Type: `application/x-www-form-urlencoded`
    - Fields: `username` (email), `password`
    - Success: sets the same HttpOnly JWT cookie used by Google OAuth and redirects the browser to the frontend dashboard URL from `FRONTEND_URL`

- GET `/auth/google` — Redirect to Google for OAuth sign-in.
- GET `/auth/google/callback` — Google callback: on success the server sets the same HttpOnly cookie containing the JWT and redirects the browser to the frontend dashboard URL from `FRONTEND_URL` instead of returning JSON.

- GET `/users/me/` — Get current user (requires auth)
- GET `/users/me/public` — Public profile of current user (no auth required)
- GET `/users/debug` — Debug helper (dev only)
- GET `/users/auth` — Auth check (requires auth)

Frontend dashboard recommendation:

- Use `GET /users/auth` when you want the authenticated user payload for the dashboard header/profile area.
- Keep browser requests on the same host as the auth cookie, for example frontend on `http://localhost:5173` and API on `http://localhost:8000`.
- Always include credentials in browser requests so the HttpOnly cookie is sent.

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

- Analytics
    - POST `/analytics/focus-sessions` — Record a completed Pomodoro session (requires auth)
        - Body: `FocusSessionCreate` { session_duration_minutes (int), completed_at (date-time), date (date) }
        - Response: { message, session_id, daily_total_minutes }
    - GET `/analytics/focus-time` — Fetch aggregated focus time for the current user (requires auth)
        - Query params: `date` (date, optional), `range` (`day`, `week`, `month`, optional)
        - Response: { date, total_minutes, sessions_count, avg_session_minutes, focus_time_display }

Request/response examples

- Register example

```bash
curl -X POST http://localhost:8000/register \
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
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alex@example.com&password=secret"
```

- Record a completed focus session:

```bash
curl -X POST http://localhost:8000/analytics/focus-sessions \
    -H "Content-Type: application/json" \
    -H "Cookie: access_token=<jwt>" \
    -d '{"session_duration_minutes":25,"completed_at":"2026-05-16T22:45:00Z","date":"2026-05-16"}'
```

- Fetch daily focus time:

```bash
curl "http://localhost:8000/analytics/focus-time?date=2026-05-16&range=day" \
    -H "Cookie: access_token=<jwt>"
```

Frontend integration notes

- Use the OpenAPI JSON at `/openapi.json` to generate typed clients (e.g., TypeScript via openapi-generator or `openapi-typescript`).
- For auth flows, the server supports two ways to provide the JWT to protected endpoints:

- Cookie (recommended for browser flows): the server can set a secure, HttpOnly cookie named by `ACCESS_COOKIE_NAME` (defaults to `access_token`) after OAuth or login. When using cookies from the browser, include credentials in requests (for `fetch`, use `credentials: 'include'`).
- Authorization header: `Authorization: Bearer <token>` — still supported for non-browser clients.

Cookie security behavior:

- The cookie is marked `Secure` automatically on HTTPS.
- For local HTTP development, set `COOKIE_SECURE=false` so the browser will store the cookie.

- Google OAuth: call `/auth/google` from the browser (redirect). After successful sign-in the server will set the JWT cookie and redirect the browser to the frontend dashboard URL from `FRONTEND_URL`.

Environment variables related to this flow:

- `FRONTEND_URL`: absolute URL of the frontend dashboard to redirect to after login, for example `http://localhost:5173/app/dashboard`.
- `ACCESS_COOKIE_NAME`: cookie name for the JWT (default: `access_token`).
- `COOKIE_DOMAIN`: optional cookie domain to set on the cookie.
- `COOKIE_SECURE`: set to `true` to force the auth cookie to be marked `Secure` even outside HTTPS.
- `COOKIE_SAMESITE`: cookie SameSite policy (`lax`, `strict`, or `none`; default: `lax`).
- `CORS_ALLOW_ORIGINS`: comma-separated list of frontend origins allowed to send credentialed requests to the API.

Important local-dev note:

- Since your frontend runs on `localhost:5173`, keep `FRONTEND_URL` and `CORS_ALLOW_ORIGINS` on `localhost` as well.

Example browser fetch using cookie-based auth:

```js
fetch("http://localhost:8000/goals", {
	credentials: "include",
});
```

Example frontend auth fetch for the dashboard:

```js
const response = await fetch("http://localhost:8000/users/auth", {
    credentials: "include",
});

const user = await response.json();
```

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
