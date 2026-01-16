"""OAuth providers for device integrations"""

from myome.integrations.oauth.base import OAuthProvider, OAuthTokens
from myome.integrations.oauth.whoop import WhoopOAuth
from myome.integrations.oauth.withings import WithingsOAuth

__all__ = [
    "OAuthProvider",
    "OAuthTokens",
    "WhoopOAuth",
    "WithingsOAuth",
]
