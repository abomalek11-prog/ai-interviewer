import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from jose import jwt as jose_jwt

from app.core.config import settings


class OAuthError(Exception):
    pass


@dataclass
class OAuthUserInfo:
    provider_id: str
    email: str
    full_name: str


def _redirect_uri(provider: str) -> str:
    return f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/auth/oauth/{provider}/callback"


def generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def is_configured(provider: str) -> bool:
    if provider == "google":
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    if provider == "github":
        return bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)
    if provider == "x":
        return bool(settings.X_CLIENT_ID and settings.X_CLIENT_SECRET)
    if provider == "apple":
        return bool(settings.APPLE_CLIENT_ID and settings.APPLE_TEAM_ID and settings.APPLE_KEY_ID and settings.APPLE_PRIVATE_KEY)
    return False


def build_authorize_url(provider: str, state: str, code_challenge: str | None = None) -> str:
    if provider == "google":
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": _redirect_uri("google"),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    if provider == "github":
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": _redirect_uri("github"),
            "scope": "read:user user:email",
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    if provider == "x":
        params = {
            "client_id": settings.X_CLIENT_ID,
            "redirect_uri": _redirect_uri("x"),
            "response_type": "code",
            "scope": "tweet.read users.read",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}"

    if provider == "apple":
        params = {
            "client_id": settings.APPLE_CLIENT_ID,
            "redirect_uri": _redirect_uri("apple"),
            "response_type": "code",
            "scope": "name email",
            "state": state,
            "response_mode": "form_post",
        }
        return f"https://appleid.apple.com/auth/authorize?{urlencode(params)}"

    raise OAuthError(f"Unsupported provider: {provider}")


def _apple_client_secret() -> str:
    now = int(time.time())
    payload = {
        "iss": settings.APPLE_TEAM_ID,
        "iat": now,
        "exp": now + 3600,
        "aud": "https://appleid.apple.com",
        "sub": settings.APPLE_CLIENT_ID,
    }
    private_key = (settings.APPLE_PRIVATE_KEY or "").replace("\\n", "\n")
    return jose_jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": settings.APPLE_KEY_ID},
    )


def exchange_code(provider: str, code: str, code_verifier: str | None) -> OAuthUserInfo:
    if provider == "google":
        return _exchange_google(code)
    if provider == "github":
        return _exchange_github(code)
    if provider == "x":
        return _exchange_x(code, code_verifier)
    if provider == "apple":
        return _exchange_apple(code)
    raise OAuthError(f"Unsupported provider: {provider}")


def _exchange_google(code: str) -> OAuthUserInfo:
    with httpx.Client(timeout=15) as client:
        token_resp = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _redirect_uri("google"),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise OAuthError(f"Google token exchange failed: {token_resp.text}")
        access_token = token_resp.json()["access_token"]

        info_resp = client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code != 200:
            raise OAuthError(f"Google userinfo fetch failed: {info_resp.text}")
        info = info_resp.json()

    email = info.get("email")
    if not email:
        raise OAuthError("Google account has no email")
    return OAuthUserInfo(provider_id=info["sub"], email=email, full_name=info.get("name") or email.split("@")[0])


def _exchange_github(code: str) -> OAuthUserInfo:
    with httpx.Client(timeout=15) as client:
        token_resp = client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _redirect_uri("github"),
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise OAuthError(f"GitHub token exchange failed: {token_resp.text}")
        token_json = token_resp.json()
        access_token = token_json.get("access_token")
        if not access_token:
            raise OAuthError(f"GitHub token exchange failed: {token_json}")

        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
        user_resp = client.get("https://api.github.com/user", headers=headers)
        if user_resp.status_code != 200:
            raise OAuthError(f"GitHub userinfo fetch failed: {user_resp.text}")
        user = user_resp.json()

        email = user.get("email")
        if not email:
            emails_resp = client.get("https://api.github.com/user/emails", headers=headers)
            if emails_resp.status_code == 200:
                for entry in emails_resp.json():
                    if entry.get("primary") and entry.get("verified"):
                        email = entry.get("email")
                        break
                if not email:
                    for entry in emails_resp.json():
                        if entry.get("verified"):
                            email = entry.get("email")
                            break

    if not email:
        raise OAuthError("GitHub account has no accessible verified email; grant email access and retry")
    return OAuthUserInfo(
        provider_id=str(user["id"]),
        email=email,
        full_name=user.get("name") or user.get("login") or email.split("@")[0],
    )


def _exchange_x(code: str, code_verifier: str | None) -> OAuthUserInfo:
    if not code_verifier:
        raise OAuthError("Missing PKCE verifier for X login")

    with httpx.Client(timeout=15) as client:
        token_resp = client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "client_id": settings.X_CLIENT_ID,
                "code": code,
                "redirect_uri": _redirect_uri("x"),
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
            auth=(settings.X_CLIENT_ID or "", settings.X_CLIENT_SECRET or ""),
        )
        if token_resp.status_code != 200:
            raise OAuthError(f"X token exchange failed: {token_resp.text}")
        access_token = token_resp.json()["access_token"]

        info_resp = client.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code != 200:
            raise OAuthError(f"X userinfo fetch failed: {info_resp.text}")
        data = info_resp.json()["data"]

    # X's standard API does not expose verified email addresses.
    synthetic_email = f"x_{data['id']}@users.noreply.x.com"
    return OAuthUserInfo(provider_id=data["id"], email=synthetic_email, full_name=data.get("name") or data.get("username"))


def _exchange_apple(code: str) -> OAuthUserInfo:
    client_secret = _apple_client_secret()
    with httpx.Client(timeout=15) as client:
        token_resp = client.post(
            "https://appleid.apple.com/auth/token",
            data={
                "client_id": settings.APPLE_CLIENT_ID,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": _redirect_uri("apple"),
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise OAuthError(f"Apple token exchange failed: {token_resp.text}")
        id_token = token_resp.json()["id_token"]

        jwks = client.get("https://appleid.apple.com/auth/keys").json()

    header = jose_jwt.get_unverified_header(id_token)
    key = next((k for k in jwks["keys"] if k["kid"] == header["kid"]), None)
    if key is None:
        raise OAuthError("Apple signing key not found")

    claims = jose_jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=settings.APPLE_CLIENT_ID,
        issuer="https://appleid.apple.com",
    )
    email = claims.get("email")
    if not email:
        raise OAuthError("Apple account has no email")
    return OAuthUserInfo(provider_id=claims["sub"], email=email, full_name=email.split("@")[0])
