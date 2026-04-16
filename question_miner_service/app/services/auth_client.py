"""auth_client.py — auto-refreshing JWT client for the Auth-service.

The Question-service's admin endpoints require a valid Bearer JWT.
Rather than relying on a static token baked into .env (which expires in 15 min),
this client logs in with the configured admin credentials, caches the access
token, and transparently re-fetches it when it is close to expiry.
"""
import time
from typing import Optional

import httpx

from app.config import Settings


# Refresh the token 60 s before it actually expires to avoid edge-case 401s.
_EXPIRY_BUFFER_SECONDS = 60


class AuthClient:
    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._settings = settings

        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0  # epoch seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_token(self) -> Optional[str]:
        """Return a valid Bearer token, refreshing if necessary.

        Returns None if no admin credentials are configured (the caller should
        then proceed without an Authorization header and will receive a 403 from
        the Question-service — which is expected when auth is not configured).
        """
        if not self._has_credentials():
            return None

        if self._token_is_stale():
            await self._refresh()

        return self._access_token

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _has_credentials(self) -> bool:
        return bool(
            self._settings.auth_service_admin_username
            and self._settings.auth_service_admin_password
        )

    def _token_is_stale(self) -> bool:
        return time.time() >= (self._expires_at - _EXPIRY_BUFFER_SECONDS)

    async def _refresh(self) -> None:
        """POST /auth/login and cache the returned access token."""
        url = (
            self._settings.auth_service_base_url.rstrip("/") + "/auth/login"
        )
        payload = {
            "username": self._settings.auth_service_admin_username,
            "password": self._settings.auth_service_admin_password,
        }
        response = await self._http_client.post(
            url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()

        body = response.json()
        # Auth-service wraps the token in ApiResponse<AuthResponse>:
        #   { "status": "success", "message": "...", "data": { "accessToken": "...", ... } }
        data = body.get("data") or body  # tolerate both shapes
        access_token: str = (
            data.get("accessToken")
            or data.get("access_token")
            or data.get("token")
        )
        if not access_token:
            raise ValueError(
                f"Auth-service /auth/login response did not contain an access token: {body}"
            )

        # Access tokens are valid for 15 minutes (900 s) per Auth-service config.
        self._access_token = access_token
        self._expires_at = time.time() + 900  # matches ACCESS_TOKEN_EXPIRY in JwtUtil
