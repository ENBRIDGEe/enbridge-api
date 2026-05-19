from typing import Annotated
from fastapi import Depends, HTTPException, Request, APIRouter, status
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi.responses import JSONResponse, RedirectResponse
from httpx import ConnectError, ConnectTimeout, ReadTimeout
from authlib.jose import JsonWebKey, JsonWebToken
from datetime import timedelta
from .auth import (
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    create_user,
    get_user,
    normalize_email,
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
    client_kwargs={"scope": "openid email profile", "timeout": 30},
)


def get_or_create_google_user(user_info: dict):
    email = normalize_email(user_info.get("email", ""))
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


async def decode_google_id_token(token: dict) -> dict | None:
    if not token.get("id_token"):
        return None

    metadata = await oauth.google.load_server_metadata()
    alg_values = metadata.get("id_token_signing_alg_values_supported") or ["RS256"]
    jwt = JsonWebToken(alg_values)
    jwk_set = await oauth.google.fetch_jwk_set()

    claims = jwt.decode(
        token["id_token"],
        key=JsonWebKey.import_key_set(jwk_set),
        claims_options={
            "iss": {"values": [metadata["issuer"]]},
            "aud": {"values": [get_settings().GOOGLE_CLIENT_ID]},
        },
    )
    claims.validate(leeway=120)
    return dict(claims)


# Redirect user to Google for authentication
@router.get("/auth/google")
async def auth_google(request: Request, settings: Annotated[Settings, Depends(get_settings)]):
    redirect_uri = settings.GOOGLE_REDIRECT_URI or str(request.url_for("google_callback"))

    # If the client expects JSON (likely an XHR), return the auth URL instead of redirecting.
    if "application/json" in request.headers.get("accept", "") or request.headers.get("x-requested-with"):
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
            user_info = await decode_google_id_token(token)
        if not user_info:
            response = await oauth.google.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
            user_info = response.json()

        user = get_or_create_google_user(user_info)

        # Create tokens
        access_token = create_access_token(
            settings,
            data={"sub": user["email"]},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            auth_method="google",
        )
        refresh_token = create_refresh_token()
        store_refresh_token(user["id"], refresh_token, settings)

        # Redirect to frontend with tokens in query params
        frontend_url = settings.FRONTEND_URL or "http://localhost:5173/app/dashboard"
        redirect_url = f"{frontend_url}?access_token={access_token}&refresh_token={refresh_token}&auth_method=google"
        return RedirectResponse(url=redirect_url)

    except MismatchingStateError as mse:
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
