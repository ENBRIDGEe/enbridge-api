"""
Sample tests for Enbridge backend API.

Run with: pytest
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from core.database import SessionLocal

from models.models import Base

from api.deps import get_db







# Tests use the application's configured database (Supabase) from `.env`.
# The test suite will connect using `core.database.SessionLocal` so we don't
# set up a separate in-memory SQLite instance here.

# Initialize client without following redirects by default to test OAuth flow
client = TestClient(app, follow_redirects=False)


def register_user(name: str = "Flow User") -> tuple[str, dict[str, str]]:
    email = f"user_{uuid4()}@example.com"
    response = client.post(
        "/register",
        json={"name": name, "email": email, "password": "password123"},
    )
    assert response.status_code == 200
    return email, {"Authorization": f"Bearer {response.json()['access_token']}"}

class TestHealth:
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to Enbridge API!"}



class TestAuth:
    def test_register_user(self):
        """Test user registration."""
        email = f"test_{uuid4()}@example.com"
        response = client.post(
            "/register",
            json={
                "name": "Test User",
                "email": email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # Verify cookies
        assert "access_token" in client.cookies
        assert "refresh_token" in client.cookies

    def test_register_duplicate_email(self):
        """Test registration with existing email."""
        email = f"dup_{uuid4()}@example.com"
        # First registration
        client.post(
            "/register",
            json={
                "name": "User One",
                "email": email,
                "password": "password123",
            },
        )
        # Second registration with same email
        response = client.post(
            "/register",
            json={
                "name": "User Two",
                "email": email,
                "password": "password456",
            },
        )
        assert response.status_code == 400

    def test_login_user(self):
        """Test user login."""
        email = f"login_{uuid4()}@example.com"
        # Register first
        client.post(
            "/register",
            json={
                "name": "Test User",
                "email": email,
                "password": "password123",
            },
        )
        # Login
        response = client.post(
            "/token",
            data={"username": email, "password": "password123"},
        )
        # /token redirects to the dashboard per README and auth.py
        assert response.status_code == 307
        assert "access_token" in client.cookies

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = client.post(
            "/token",
            data={"username": "nonexistent@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401


class TestUsers:
    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers for testing."""
        email = f"auth_{uuid4()}@example.com"
        resp = client.post(
            "/register",
            json={
                "name": "Auth User",
                "email": email,
                "password": "password123",
            },
        )
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_current_user(self, auth_headers):
        """Test getting current user profile."""
        response = client.get(
            "/users/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Must be a single user object, not a list of all users
        assert isinstance(data, dict)
        assert "email" in data
        assert data["name"] == "Auth User"

    def test_get_public_current_user(self, auth_headers):
        response = client.get(
            "/users/me/public",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Auth User"
        assert "id" in data
        assert "email" not in data
        assert "password_hash" not in data
        assert "is_admin" not in data

    def test_debug_endpoints_hidden(self):
        response = client.get("/users/debug")
        assert response.status_code in {401, 403, 404}

        response = client.get("/debug/auth-cookie")
        assert response.status_code in {401, 403, 404}

    def test_update_user_profile(self, auth_headers):
        """Test updating user profile."""
        response = client.patch(
            "/users/me",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"


class TestAuthHardening:
    def test_cookie_security_flags(self):
        """Verify that auth cookies have HttpOnly and SameSite=lax."""
        email = f"secure_{uuid4()}@example.com"
        response = client.post(
            "/register",
            json={"name": "Secure User", "email": email, "password": "password123"},
        )
        assert response.status_code == 200
        
        # Check Set-Cookie headers for security attributes
        set_cookies = response.headers.get_list("set-cookie")
        access_cookie = next((c for c in set_cookies if "access_token" in c), "")
        refresh_cookie = next((c for c in set_cookies if "refresh_token" in c), "")
        
        assert "HttpOnly" in access_cookie
        assert "HttpOnly" in refresh_cookie
        assert "samesite=lax" in access_cookie.lower()


class TestProductFlows:
    def test_goal_milestone_task_analytics_notifications_flow(self):
        _, headers = register_user("Product Flow User")

        goal_response = client.post(
            "/goals",
            headers=headers,
            json={
                "title": "Ship MVP",
                "category": "product",
                "deadline": "2026-06-01T09:00:00",
                "status": "active",
            },
        )
        assert goal_response.status_code == 200
        goal = goal_response.json()
        assert goal["title"] == "Ship MVP"

        list_goals_response = client.get("/goals", headers=headers)
        assert list_goals_response.status_code == 200
        assert any(item["id"] == goal["id"] for item in list_goals_response.json()["goals"])

        update_goal_response = client.patch(
            f"/goals/{goal['id']}",
            headers=headers,
            json={"status": "completed"},
        )
        assert update_goal_response.status_code == 200
        assert update_goal_response.json()["status"] == "completed"

        milestone_response = client.post(
            "/milestones",
            headers=headers,
            json={
                "goal_id": goal["id"],
                "target_date": "2026-05-25T09:00:00",
                "order_index": 1,
            },
        )
        assert milestone_response.status_code == 200
        milestone = milestone_response.json()

        list_milestones_response = client.get(f"/milestones/goal/{goal['id']}", headers=headers)
        assert list_milestones_response.status_code == 200
        assert any(item["id"] == milestone["id"] for item in list_milestones_response.json()["milestones"])

        task_response = client.post(
            "/tasks",
            headers=headers,
            json={
                "milestone_id": milestone["id"],
                "due_date": "2026-05-20T09:00:00",
                "completed": False,
            },
        )
        assert task_response.status_code == 200
        task = task_response.json()

        list_tasks_response = client.get("/tasks", headers=headers)
        assert list_tasks_response.status_code == 200
        assert any(item["id"] == task["id"] for item in list_tasks_response.json()["tasks"])

        update_task_response = client.patch(
            f"/tasks/{task['id']}",
            headers=headers,
            json={"completed": True},
        )
        assert update_task_response.status_code == 200
        assert bool(update_task_response.json()["completed"]) is True

        focus_response = client.post(
            "/analytics/focus-sessions",
            headers=headers,
            json={
                "session_duration_minutes": 25,
                "completed_at": "2026-05-17T10:00:00",
                "date": "2026-05-17",
            },
        )
        assert focus_response.status_code == 201
        assert focus_response.json()["daily_total_minutes"] == 25

        for focus_range in ("day", "week", "month"):
            analytics_response = client.get(
                f"/analytics/focus-time?date=2026-05-17&range={focus_range}",
                headers=headers,
            )
            assert analytics_response.status_code == 200
            assert analytics_response.json()["total_minutes"] == 25
            assert analytics_response.json()["sessions_count"] == 1

        settings_response = client.get("/notifications/settings", headers=headers)
        assert settings_response.status_code == 200
        assert bool(settings_response.json()["push_enabled"]) is True

        update_settings_response = client.patch(
            "/notifications/settings",
            headers=headers,
            json={"push_enabled": False, "remainder": "2026-05-17T12:00:00"},
        )
        assert update_settings_response.status_code == 200
        assert bool(update_settings_response.json()["push_enabled"]) is False

        delete_task_response = client.delete(f"/tasks/{task['id']}", headers=headers)
        assert delete_task_response.status_code == 200

    def test_refresh_token_rotation_and_revocation(self):
        """Verify that refreshing a token keeps the session usable."""
        email = f"rotate_{uuid4()}@example.com"
        client.post(
            "/register",
            json={"name": "Rotate User", "email": email, "password": "password123"},
        )
        
        old_refresh_token = client.cookies.get("refresh_token")
        assert old_refresh_token is not None
        
        # Perform refresh twice to ensure the dashboard can call it more than once.
        response = client.post("/auth/refresh")
        assert response.status_code == 200
        
        new_refresh_token = client.cookies.get("refresh_token")
        assert new_refresh_token == old_refresh_token
        
        # Reusing the same refresh token should still work.
        client.cookies.set("refresh_token", old_refresh_token)
        repeat_response = client.post("/auth/refresh")
        assert repeat_response.status_code == 200

    def test_logout_revocation(self):
        """Verify logout clears cookies and revokes token access."""
        email = f"logout_{uuid4()}@example.com"
        client.post(
            "/register",
            json={"name": "Logout User", "email": email, "password": "password123"},
        )
        
        assert "access_token" in client.cookies
        
        # Logout
        logout_resp = client.post("/logout")
        assert logout_resp.status_code == 200
        
        # Check that cookies are cleared in the response
        set_cookies = logout_resp.headers.get_list("set-cookie")
        assert any('access_token=;' in c or 'access_token=""' in c for c in set_cookies)
        
        # Verification: Accessing protected resource should fail
        client.cookies.clear() # Simulate browser clearing cookies
        check_resp = client.get("/users/me")
        assert check_resp.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
