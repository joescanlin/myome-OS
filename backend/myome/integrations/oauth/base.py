"""Base OAuth provider class"""

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx


@dataclass
class OAuthTokens:
    """OAuth token response"""

    access_token: str
    refresh_token: str | None
    expires_at: datetime
    token_type: str = "Bearer"
    scope: str | None = None

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at

    def to_dict(self) -> dict:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "token_type": self.token_type,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthTokens":
        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
        )


class OAuthProvider(ABC):
    """Base class for OAuth 2.0 providers"""

    provider_name: str = "base"
    authorization_url: str = ""
    token_url: str = ""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self._http_client: httpx.AsyncClient | None = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def generate_state(self) -> str:
        """Generate a random state token for CSRF protection"""
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str) -> str:
        """Build the authorization URL for user redirect"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
        }
        params.update(self._extra_auth_params())
        return f"{self.authorization_url}?{urlencode(params)}"

    def _extra_auth_params(self) -> dict:
        """Override to add provider-specific auth params"""
        return {}

    @abstractmethod
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens"""
        pass

    @abstractmethod
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired access token"""
        pass

    async def _token_request(self, data: dict) -> OAuthTokens:
        """Make token request to provider"""
        response = await self.http_client.post(
            self.token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return self._parse_token_response(response.json())

    @abstractmethod
    def _parse_token_response(self, data: dict) -> OAuthTokens:
        """Parse provider-specific token response"""
        pass
