"""Withings OAuth provider"""

from datetime import datetime, timedelta, timezone

from myome.integrations.oauth.base import OAuthProvider, OAuthTokens


class WithingsOAuth(OAuthProvider):
    """OAuth 2.0 implementation for Withings API"""
    
    provider_name = "withings"
    authorization_url = "https://account.withings.com/oauth2_user/authorize2"
    token_url = "https://wbsapi.withings.net/v2/oauth2"
    
    # Default scopes for health data
    DEFAULT_SCOPES = [
        "user.metrics",    # Weight, body composition, blood pressure
        "user.activity",   # Activity and sleep data
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
    
    def _extra_auth_params(self) -> dict:
        """Withings uses comma-separated scopes"""
        return {
            "scope": ",".join(self.scopes),  # Override default space-separated
        }
    
    def get_authorization_url(self, state: str) -> str:
        """Build Withings authorization URL"""
        from urllib.parse import urlencode
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": ",".join(self.scopes),
            "state": state,
        }
        return f"{self.authorization_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str) -> OAuthTokens:
        """Exchange authorization code for tokens"""
        data = {
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        return await self._token_request(data)
    
    async def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """Refresh expired access token"""
        data = {
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        return await self._token_request(data)
    
    def _parse_token_response(self, data: dict) -> OAuthTokens:
        """Parse Withings token response (nested in 'body')"""
        # Withings wraps response in status/body structure
        if "body" in data:
            body = data["body"]
        else:
            body = data
        
        expires_in = body.get("expires_in", 10800)  # Default 3 hours
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        return OAuthTokens(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            expires_at=expires_at,
            token_type=body.get("token_type", "Bearer"),
            scope=body.get("scope"),
        )
