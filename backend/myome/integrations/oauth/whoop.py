"""Whoop OAuth provider"""

from datetime import datetime, timedelta, timezone

from myome.integrations.oauth.base import OAuthProvider, OAuthTokens


class WhoopOAuth(OAuthProvider):
    """OAuth 2.0 implementation for Whoop API"""
    
    provider_name = "whoop"
    authorization_url = "https://api.prod.whoop.com/oauth/oauth2/auth"
    token_url = "https://api.prod.whoop.com/oauth/oauth2/token"
    
    # Default scopes for comprehensive health data
    DEFAULT_SCOPES = [
        "read:recovery",
        "read:cycles",
        "read:workout",
        "read:sleep",
        "read:profile",
        "read:body_measurement",
        "offline",  # Required for refresh tokens
    ]
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
    ):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes or self.DEFAULT_SCOPES,
        )
    
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for access and refresh tokens"""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        return await self._token_request(data)
    
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired access token"""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        return await self._token_request(data)
    
    def _parse_token_response(self, data: dict) -> OAuthTokens:
        """Parse Whoop token response"""
        expires_in = data.get("expires_in", 3600)  # Default 1 hour
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
        )
