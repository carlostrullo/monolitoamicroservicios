import asyncio
import json

import httpx
import jwt
from cachetools import TTLCache
from fastapi import Request

from app.config import Settings


_jwks_cache = TTLCache(maxsize=2, ttl=300)
_jwks_lock = asyncio.Lock()


class AuthError(Exception):
    def __init__(self, error: str, status_code: int = 401, details: str | None = None):
        self.error = error
        self.status_code = status_code
        self.details = details
        super().__init__(error)


def is_public_path(path: str) -> bool:
    if path == "/health":
        return True
    if path == "/openapi.json":
        return True
    if path.startswith("/docs"):
        return True
    return False


def _get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        raise AuthError("missing_authorization_header", 401)

    if not auth_header.startswith("Bearer "):
        raise AuthError("invalid_authorization_header", 401)

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise AuthError("missing_bearer_token", 401)

    return token


async def _fetch_jwks(client: httpx.AsyncClient, settings: Settings) -> dict:
    if "jwks" in _jwks_cache:
        return _jwks_cache["jwks"]

    if not settings.oidc_jwks_url:
        raise AuthError("jwks_url_not_configured", 500)

    async with _jwks_lock:
        if "jwks" in _jwks_cache:
            return _jwks_cache["jwks"]

        try:
            response = await client.get(settings.oidc_jwks_url)
            response.raise_for_status()
            jwks = response.json()
            _jwks_cache["jwks"] = jwks
            return jwks
        except httpx.HTTPError as exc:
            raise AuthError("jwks_unavailable", 503, str(exc)) from exc


async def _get_signing_key(token: str, client: httpx.AsyncClient, settings: Settings):
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
    except jwt.InvalidTokenError as exc:
        raise AuthError("invalid_token_header", 401, str(exc)) from exc

    jwks = await _fetch_jwks(client, settings)
    keys = jwks.get("keys", [])
    jwk = next((key for key in keys if key.get("kid") == kid), None)

    if not jwk:
        _jwks_cache.pop("jwks", None)
        jwks = await _fetch_jwks(client, settings)
        keys = jwks.get("keys", [])
        jwk = next((key for key in keys if key.get("kid") == kid), None)

    if not jwk:
        raise AuthError("signing_key_not_found", 401)

    return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))


def decode_and_verify(token: str, signing_key, settings: Settings) -> dict:
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": settings.oidc_verify_aud,
        "verify_iss": settings.oidc_verify_iss,
    }

    kwargs = {
        "key": signing_key,
        "algorithms": ["RS256"],
        "options": options,
    }

    if options["verify_iss"] and settings.oidc_issuer:
        kwargs["issuer"] = settings.oidc_issuer

    if options["verify_aud"] and settings.oidc_audience:
        kwargs["audience"] = settings.oidc_audience

    try:
        return jwt.decode(token, **kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token_expired", 401) from exc
    except jwt.InvalidIssuerError as exc:
        raise AuthError("invalid_issuer", 401) from exc
    except jwt.InvalidAudienceError as exc:
        raise AuthError("invalid_audience", 401) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("invalid_token", 401, str(exc)) from exc


def extract_roles(payload: dict) -> set[str]:
    roles: set[str] = set()

    realm_roles = payload.get("realm_access", {}).get("roles", []) or []
    roles.update(realm_roles)

    resource_access = payload.get("resource_access", {}) or {}
    for client_info in resource_access.values():
        roles.update(client_info.get("roles", []) or [])

    return roles


async def authenticate_request(
    request: Request,
    client: httpx.AsyncClient,
    settings: Settings,
) -> None:
    if not settings.auth_enabled or is_public_path(request.url.path):
        return

    token = _get_bearer_token(request)
    signing_key = await _get_signing_key(token, client, settings)
    payload = decode_and_verify(token, signing_key, settings)
    roles = extract_roles(payload)

    request.state.auth_token = token
    request.state.auth_payload = payload
    request.state.auth_roles = roles
