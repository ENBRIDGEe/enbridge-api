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
cd /Users/kritimantalukdar/Desktop/Client/enbridge-api
source .venv/bin/activate
pip install -r requirements.txt
./.venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Environment (backend/.env)

- The app reads lowercase DB parts: `user`, `password`, `host`, `port`, `dbname`. If all present the app builds the Postgres `DATABASE_URL`. Otherwise it falls back to `sqlite:///./enbridge.db`.
- Required for production: `SECRET_KEY`, DB credentials, Google OAuth keys (if using Google sign-in).

Live database schema notes

- The live database currently has these core tables: `users`, `goals`, `milestones`, `goal_activity`, `notification_settings`, `progress_logs`, `refresh_tokens`, `subscriptions`, `tasks`, and `focus_sessions`.
- The ORM and request schemas in this repo are aligned to those table shapes, including the newer fields such as `goal_activity.activity_date`, `goals.progress_percentage`, `tasks.milestone_id`, `tasks.completed_at`, and `notification_settings.email_enabled` / `reminder_time` / `timezone`.
- Some endpoints keep backward-compatible request aliases where practical. For example, `NotificationUpdate` still accepts `remainder` as an alias for `reminder_time`.
- Refresh-token auth now uses the `refresh_tokens` table as the source of truth. The old `users.refresh_token_*` columns are legacy and no longer part of the application logic.

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
- POST `/auth/refresh` — Rotate the refresh token and issue a new access-token cookie.
- POST `/logout` — Revoke the refresh token and clear auth cookies.

Refresh token endpoint

- **POST `/auth/refresh`** — Reissue the access token cookie using the current refresh token cookie.
    - Purpose: Accepts the current refresh token from the HttpOnly `refresh_token` cookie, validates it, and issues a fresh access token cookie used for authenticated requests. The existing refresh token remains valid until logout or expiry, which makes the endpoint safe to call multiple times during dashboard startup.
    - Authentication: The endpoint reads the `refresh_token` cookie; no `Authorization` header required for rotation flows.
    - Success: Returns `200 OK`, keeps the existing `refresh_token` cookie in place, and sets a fresh `access_token` cookie. The response body may include a short JSON status payload.
    - Failure: Returns `401 Unauthorized` when the refresh token is missing, invalid, or expired. On failure the server will clear auth cookies.

Example curl (browser flows should rely on the cookie being sent automatically):

```bash
curl -X POST http://localhost:8000/auth/refresh \
    -H "Content-Type: application/json" \
    --cookie "refresh_token=<current_refresh_token>" \
    -i
```

Notes:

- The refresh-token lookup is recorded in the `refresh_tokens` table using `token_hash`, `expires_at`, and `revoked_at` (see the migration noted above). The refresh token itself is reused until logout or expiry so dashboard startup can safely call `/auth/refresh` more than once.
- When testing with `httpx` or `curl`, ensure you forward cookies between calls to observe rotation behavior.

- GET `/users/me/` — Get current user (requires auth)
- PATCH `/users/me` — Update the current user's profile name (requires auth)
- GET `/users/me/public` — Safe public fields for the current user (requires auth)
- GET `/users/auth` — Minimal auth check helper, hidden from OpenAPI (requires auth)

Frontend dashboard recommendation:

- Use `GET /users/auth` when you want the authenticated user payload for the dashboard header/profile area.
- Keep browser requests on the same host as the auth cookie, for example frontend on `http://localhost:5173` and API on `http://localhost:8000`.
- Always include credentials in browser requests so the HttpOnly cookie is sent.
- If `/app/dashboard` keeps spinning after login, that is usually a frontend auth-guard or data-loading issue rather than a backend login failure. The backend should already have completed the redirect and set the cookies.

- Goals
    - GET `/goals` — List goals for current user (requires auth)
    - POST `/goals` — Create a goal (body: `GoalCreate`)
        - `GoalCreate`: { title, description, category, target_date (date-time), deadline (date-time), status, progress_percentage }
    - GET `/goals/{goal_id}` — Read a specific goal (requires auth)
    - PATCH `/goals/{goal_id}` — Update a goal (body: `GoalUpdate`)
    - DELETE `/goals/{goal_id}` — Delete goal
    - POST `/goals/{goal_id}/activity` — Record goal activity for a specific day
    - GET `/goals/{goal_id}/activity` — List goal activity days
    - DELETE `/goals/{goal_id}/activity` — Delete goal activity for a specific day

- Milestones
    - POST `/milestones` — Create milestone (body: `MilestoneCreate`)
        - `MilestoneCreate`: { goal_id (uuid), title (optional), description (optional), target_date (date-time), order_index (integer), completed (bool) }
    - GET `/milestones/goal/{goal_id}` — List milestones for a goal (requires auth)

- Tasks
    - GET `/tasks` — List tasks for current user (requires auth)
    - POST `/tasks` — Create task (body: `TaskCreate`)
        - `TaskCreate`: { title (optional), milestone_id (optional uuid), due_date (date-time), completed (bool) }
    - PATCH `/tasks/{task_id}` — Update task (body: `TaskUpdate`)
    - DELETE `/tasks/{task_id}` — Delete task

- Notifications
    - GET `/notifications/settings` — Read notification settings for current user (requires auth)
    - PATCH `/notifications/settings` — Update settings (body: `NotificationUpdate`)
        - `NotificationUpdate`: { push_enabled (bool), email_enabled (bool), reminder_time (time, alias `remainder` for backwards compatibility), timezone (string) }

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

Tests:

```bash
pytest -q
```

Recent changes (important)

- **Refresh-token storage**: The app now stores refresh-token rotation state in the `refresh_tokens` table. Each login writes a new row, refresh validates the active row, and logout revokes that row. A migration exists at `migrations/versions/eaa370972844_updated_refresh_token_into_user_s_table.py`.
- **Legacy user columns removed**: The `users.refresh_token_*` columns and their indexes were dropped from the live database. The new cleanup migration lives at `migrations/versions/7f9d3a6e4b21_drop_refresh_token_columns_from_users.py`.

```bash
alembic upgrade head
# Or run the SQL manually if you cannot run Alembic:
ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
```

- **Connection pooling / Supabase pooler**: When connecting to Supabase in production you should use the Supabase session pooler (host like `*.pooler.supabase.com`) and set `sslmode=require`. The app's `core/database.py` is configured to build the `DATABASE_URL` from the lowercase env vars found in `.env` (`user`, `password`, `host`, `port`, `dbname`) and uses SQLAlchemy's `NullPool` so client-side pooling is disabled (recommended when using a managed pooler).

- **Task shape**: `tasks` is now treated as the live user-owned task table with `user_id`, `title`, `completed_at`, and optional `milestone_id`. Task creation can still derive a title from the linked milestone if one is not provided.

- **Goals and activity**: Goal payloads now include `description`, `target_date`, `deadline`, and `progress_percentage`. The goal activity endpoints (`POST/GET/DELETE /goals/{goal_id}/activity`) drive the heatmap UI and persist into `goal_activity`.

- **Notifications**: The settings payload now uses `push_enabled`, `email_enabled`, `reminder_time`, and `timezone` to match the live table. The API still accepts `remainder` as an alias to preserve older clients.

- **Tasks `completed_at`**: The `tasks` table and API now include a `completed_at` field (datetime). Creating or updating a task may set or clear `completed_at` based on the `completed` boolean in the API payload.

- **Goals activity (heatmap)**: Per-day activity tracking for goals was added. New endpoints:
    - `POST /goals/{goal_id}/activity` — record activity for a day
    - `DELETE /goals/{goal_id}/activity` — remove activity for a day
    - `GET /goals/{goal_id}/activity` — list activity days for a goal

Testing notes / safety

- The test suite (`pytest -q`) uses the application's configured DB by default. Ensure your `.env` points to a safe test or development database before running the full test suite — tests will create, modify, and delete data.

If you want me to roll the Alembic migrations for you on a specific host or run the SQL directly against a DB, provide DB access (or run the provided SQL/commands on your environment).

Database & migrations

- Schema changes are managed with **Alembic migrations**.
- Before running locally, apply migrations with `alembic upgrade head`.

## Local setup for Alembic (one-time)

This repository already includes an Alembic environment:

```bash
cd /Users/kritimantalukdar/Desktop/Client/enbridge-api
alembic current
```

## Apply model changes (repeatable)

After updating your SQLAlchemy models, run:

```bash
# set DB env (.env)
source .venv/bin/activate

# generate a migration from model changes
alembic revision --autogenerate -m "update models"

# apply migration to enbridge.db / Postgres
alembic upgrade head

# verify models and DB are in sync
alembic check
```

Where to look for full schema

- The OpenAPI JSON at `/openapi.json` contains the components/schemas referenced above (UserRegister, Token, GoalCreate, GoalUpdate, MilestoneCreate, TaskCreate, TaskUpdate, NotificationUpdate). Use that file to produce client types.
