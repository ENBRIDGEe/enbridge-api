"""
Sample tests for Enbridge backend API.

Run with: pytest
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.api.deps import get_db
from app.core.database import Base


# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestHealth:
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuth:
    def test_register_user(self):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self):
        """Test registration with existing email."""
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "name": "User One",
                "email": "duplicate@example.com",
                "password": "password123",
            },
        )
        # Second registration with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "User Two",
                "email": "duplicate@example.com",
                "password": "password456",
            },
        )
        assert response.status_code == 422

    def test_login_user(self):
        """Test user login."""
        # Register first
        client.post(
            "/api/v1/auth/register",
            json={
                "name": "Test User",
                "email": "login@example.com",
                "password": "password123",
            },
        )
        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 422


class TestUsers:
    @pytest.fixture
    def auth_token(self):
        """Get authentication token for testing."""
        client.post(
            "/api/v1/auth/register",
            json={
                "name": "Auth User",
                "email": "auth@example.com",
                "password": "password123",
            },
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "auth@example.com", "password": "password123"},
        )
        return response.json()["access_token"]

    def test_get_current_user(self, auth_token):
        """Test getting current user profile."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "auth@example.com"
        assert data["name"] == "Auth User"

    def test_update_user_profile(self, auth_token):
        """Test updating user profile."""
        response = client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
