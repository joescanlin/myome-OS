"""OAuth callback routes for device integrations"""

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from myome.api.deps.auth import CurrentUser
from myome.api.deps.db import DbSession
from myome.core.config import settings
from myome.core.models import Device
from myome.integrations.oauth import OAuthTokens, WhoopOAuth, WithingsOAuth

router = APIRouter(prefix="/oauth", tags=["OAuth"])

# In-memory state storage (use Redis in production)
_oauth_states: dict[str, dict] = {}

ProviderType = Literal["whoop", "withings"]


def get_oauth_provider(provider: ProviderType):
    """Get OAuth provider instance"""
    if provider == "whoop":
        if not settings.whoop_client_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Whoop integration not configured",
            )
        return WhoopOAuth(
            client_id=settings.whoop_client_id,
            client_secret=settings.whoop_client_secret,
            redirect_uri=settings.whoop_redirect_uri,
        )
    elif provider == "withings":
        if not settings.withings_client_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Withings integration not configured",
            )
        return WithingsOAuth(
            client_id=settings.withings_client_id,
            client_secret=settings.withings_client_secret,
            redirect_uri=settings.withings_redirect_uri,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {provider}",
        )


def get_device_type_for_provider(provider: ProviderType) -> str:
    """Map provider to device type"""
    mapping = {
        "whoop": "fitness_tracker",
        "withings": "smart_scale",  # Primary device, can have multiple
    }
    return mapping.get(provider, "other")


def get_vendor_for_provider(provider: ProviderType) -> str:
    """Map provider to vendor name"""
    return provider  # whoop -> whoop, withings -> withings


@router.get("/connect/{provider}")
async def initiate_oauth(
    provider: ProviderType,
    user: CurrentUser,
) -> dict:
    """
    Initiate OAuth flow for a device provider.
    Returns the authorization URL to redirect the user to.
    """
    oauth = get_oauth_provider(provider)
    state = oauth.generate_state()

    # Store state with user info for callback verification
    _oauth_states[state] = {
        "user_id": user.id,
        "provider": provider,
    }

    auth_url = oauth.get_authorization_url(state)

    return {
        "authorization_url": auth_url,
        "state": state,
    }


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: ProviderType,
    session: DbSession,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    """
    OAuth callback endpoint. Handles the redirect from the OAuth provider.
    Exchanges code for tokens and creates/updates device record.
    """
    # Check for OAuth errors
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/devices?error={error}&description={error_description or ''}"
        )

    # Verify state
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        return RedirectResponse(
            url=f"{settings.frontend_url}/devices?error=invalid_state"
        )

    if state_data["provider"] != provider:
        return RedirectResponse(
            url=f"{settings.frontend_url}/devices?error=provider_mismatch"
        )

    user_id = state_data["user_id"]

    # Exchange code for tokens
    oauth = get_oauth_provider(provider)
    try:
        tokens = await oauth.exchange_code(code)
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/devices?error=token_exchange_failed&description={str(e)}"
        )
    finally:
        await oauth.close()

    # Create or update device record
    device = Device(
        id=str(uuid4()),
        user_id=user_id,
        name=f"{provider.title()} Device",
        device_type=get_device_type_for_provider(provider),
        vendor=get_vendor_for_provider(provider),
        is_connected=True,
        api_credentials=tokens.to_dict(),
    )

    session.add(device)
    await session.commit()

    # Redirect back to frontend with success
    return RedirectResponse(
        url=f"{settings.frontend_url}/devices?connected={provider}&device_id={device.id}"
    )


@router.post("/refresh/{device_id}")
async def refresh_device_tokens(
    device_id: str,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Manually refresh OAuth tokens for a device"""
    from sqlalchemy import select

    # Get device
    result = await session.execute(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if not device.api_credentials:
        raise HTTPException(status_code=400, detail="Device has no OAuth credentials")

    # Get current tokens
    tokens = OAuthTokens.from_dict(device.api_credentials)
    if not tokens.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")

    # Refresh tokens
    oauth = get_oauth_provider(device.vendor)  # type: ignore
    try:
        new_tokens = await oauth.refresh_tokens(tokens.refresh_token)
    finally:
        await oauth.close()

    # Update device
    device.api_credentials = new_tokens.to_dict()
    device.is_connected = True
    await session.commit()

    return {"status": "refreshed", "expires_at": new_tokens.expires_at.isoformat()}


@router.delete("/disconnect/{device_id}")
async def disconnect_device(
    device_id: str,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Disconnect a device (revoke OAuth and remove credentials)"""
    from sqlalchemy import select

    result = await session.execute(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Clear credentials and mark disconnected
    device.api_credentials = {}
    device.is_connected = False
    await session.commit()

    return {"status": "disconnected"}
