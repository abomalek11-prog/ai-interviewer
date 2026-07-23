from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.security import create_oauth_state, decode_oauth_state
from app.services.auth_service import AuthService
from app.services.oauth_providers import OAuthError, build_authorize_url, exchange_code, generate_pkce_pair, is_configured
from app.utils.dependencies import DbSession

router = APIRouter()

SUPPORTED_PROVIDERS = {"google", "github", "x", "apple"}


@router.get("/oauth/providers")
def oauth_providers() -> dict[str, bool]:
    return {provider: is_configured(provider) for provider in sorted(SUPPORTED_PROVIDERS)}


def _frontend_error_redirect(message: str) -> RedirectResponse:
    url = f"{settings.FRONTEND_BASE_URL}/login?{urlencode({'oauth_error': message})}"
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/{provider}/login")
def oauth_login(provider: str) -> RedirectResponse:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider")
    if not is_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} login is not configured on this server",
        )

    code_verifier: str | None = None
    code_challenge: str | None = None
    if provider == "x":
        code_verifier, code_challenge = generate_pkce_pair()

    state_payload = {"provider": provider}
    if code_verifier:
        state_payload["code_verifier"] = code_verifier
    state = create_oauth_state(state_payload)

    authorize_url = build_authorize_url(provider, state, code_challenge)
    return RedirectResponse(authorize_url, status_code=status.HTTP_302_FOUND)


def _handle_callback(provider: str, code: str | None, state: str | None, db) -> RedirectResponse:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider")
    if not code or not state:
        return _frontend_error_redirect("missing_code_or_state")

    try:
        state_payload = decode_oauth_state(state)
    except ValueError:
        return _frontend_error_redirect("invalid_state")

    if state_payload.get("provider") != provider:
        return _frontend_error_redirect("provider_mismatch")

    try:
        user_info = exchange_code(provider, code, state_payload.get("code_verifier"))
    except OAuthError:
        return _frontend_error_redirect("exchange_failed")

    service = AuthService(db)
    user = service.find_or_create_oauth_user(
        provider=provider,
        provider_id=user_info.provider_id,
        email=user_info.email,
        full_name=user_info.full_name,
    )
    tokens = service.create_token_pair(user)

    query = urlencode({"access_token": tokens.access_token, "refresh_token": tokens.refresh_token})
    redirect_url = f"{settings.FRONTEND_BASE_URL}/auth/callback?{query}"
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)


@router.get("/oauth/{provider}/callback")
def oauth_callback_get(provider: str, db: DbSession, code: str | None = None, state: str | None = None) -> RedirectResponse:
    return _handle_callback(provider, code, state, db)


@router.post("/oauth/{provider}/callback")
async def oauth_callback_post(
    provider: str,
    db: DbSession,
    code: str | None = Form(default=None),
    state: str | None = Form(default=None),
) -> RedirectResponse:
    return _handle_callback(provider, code, state, db)
