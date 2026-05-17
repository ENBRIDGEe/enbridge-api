from typing import Annotated
from fastapi import Depends, HTTPException, Request, APIRouter, status
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi.responses import JSONResponse
from httpx import ConnectError, ConnectTimeout, ReadTimeout
from .auth import (
    create_user_session,
    create_user,
    get_user,
)
from core.config import Settings
from functools import lru_cache

router = APIRouter()


@lru_cache
def get_settings():
    return Settings()

# Configure OAuth
oauth = OAuth()
oauth.register(
    name="google",
    client_id=get_settings().GOOGLE_CLIENT_ID,
    client_secret=get_settings().GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    authorize_params={"scope": "openid email profile"},
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={"scope": "openid email profile"},
)


def get_or_create_google_user(user_info: dict):
    email = user_info.get("email")
    name = user_info.get("name") or email

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an email address",
        )

    existing_user = get_user(email)
    if existing_user:
        return existing_user

    user, created = create_user(name, email, "")
    return user


# Redirect user to Google for authentication
@router.get("/auth/google")
async def auth_google(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    redirect_uri = settings.GOOGLE_REDIRECT_URI or str(request.url_for("google_callback"))

    # If the client expects JSON (likely an XHR), return the auth URL instead of redirecting.
    # NOTE: A top-level navigation is required for OAuth so the browser stores the session cookie.
    if "application/json" in request.headers.get("accept", "") or request.headers.get("x-requested-with"):
        # Build the redirect response and extract Location header
        resp = await oauth.google.authorize_redirect(request, redirect_uri=redirect_uri)
        location = resp.headers.get("location")
        return JSONResponse({"auth_url": location, "note": "Use window.location.href = auth_url to start OAuth (must be a top-level navigation)."})

    return await oauth.google.authorize_redirect(request, redirect_uri=redirect_uri)


# Handle the OAuth callback from Google
@router.get("/auth/google/callback")
async def google_callback(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            response = await oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
            user_info = response.json()

        user = get_or_create_google_user(user_info)

        return create_user_session(request, user, settings, auth_method="google")
    except MismatchingStateError as mse:
        # Provide a clearer error explaining common causes and remediation steps
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "OAuth state mismatch (CSRF). Common causes: frontend initiated the flow via XHR instead of a top-level navigation, "
                "inconsistent hostnames (localhost vs 127.0.0.1), or cookie SameSite/Secure settings blocking the session cookie. "
                "Ensure you navigate the browser to /auth/google (e.g., `window.location.href = '/auth/google'`), clear cookies for localhost, "
                "and verify GOOGLE_REDIRECT_URI exactly matches the value registered in Google Cloud Console."
            ),
        )
    except (ConnectTimeout, ReadTimeout, ConnectError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Could not reach Google from the backend. Check your internet connection, VPN, proxy, firewall, or try again.",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
