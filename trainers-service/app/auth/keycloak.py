import json
import os
from functools import wraps

import jwt
import requests
from cachetools import TTLCache
from flask import g, jsonify, request

_jwks_cache = TTLCache(maxsize=2, ttl=300)


class AuthError(Exception):
    def __init__(self, error: str, status_code: int = 401, details: str | None = None):
        self.error = error
        self.status_code = status_code
        self.details = details
        super().__init__(error)


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def auth_enabled() -> bool:
    return _env_bool("AUTH_ENABLED", "0")


def _oidc_issuer() -> str:
    return os.getenv("OIDC_ISSUER", "").strip()


def _oidc_jwks_url() -> str:
    return os.getenv("OIDC_JWKS_URL", "").strip()


def _oidc_verify_iss() -> bool:
    return _env_bool("OIDC_VERIFY_ISS", "1")


def _oidc_verify_aud() -> bool:
    return _env_bool("OIDC_VERIFY_AUD", "0")


def _oidc_audience() -> str:
    return os.getenv("OIDC_AUDIENCE", "").strip()


def _get_bearer_token() -> str:
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header:
        raise AuthError("missing_authorization_header", 401)

    if not auth_header.startswith("Bearer "):
        raise AuthError("invalid_authorization_header", 401)

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise AuthError("missing_bearer_token", 401)
    return token


def _fetch_jwks() -> dict:
    if "jwks" in _jwks_cache:
        return _jwks_cache["jwks"]

    jwks_url = _oidc_jwks_url()
    if not jwks_url:
        raise AuthError("jwks_url_not_configured", 500)

    try:
        resp = requests.get(jwks_url, timeout=5)
        resp.raise_for_status()
        jwks = resp.json()
        _jwks_cache["jwks"] = jwks
        return jwks
    except requests.RequestException as e:
        raise AuthError("jwks_unavailable", 503, str(e))


def _get_signing_key(token: str):
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
    except jwt.InvalidTokenError as e:
        raise AuthError("invalid_token_header", 401, str(e))

    jwks = _fetch_jwks()
    keys = jwks.get("keys", [])
    jwk = next((k for k in keys if k.get("kid") == kid), None)

    if not jwk:
        # refresca caché una vez por si rotó la key
        _jwks_cache.pop("jwks", None)
        jwks = _fetch_jwks()
        keys = jwks.get("keys", [])
        jwk = next((k for k in keys if k.get("kid") == kid), None)

    if not jwk:
        raise AuthError("signing_key_not_found", 401)

    return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))


def decode_and_verify(token: str) -> dict:
    signing_key = _get_signing_key(token)

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": _oidc_verify_aud(),
        "verify_iss": _oidc_verify_iss(),
    }

    kwargs = {
        "key": signing_key,
        "algorithms": ["RS256"],
        "options": options,
    }

    issuer = _oidc_issuer()
    if options["verify_iss"] and issuer:
        kwargs["issuer"] = issuer

    audience = _oidc_audience()
    if options["verify_aud"] and audience:
        kwargs["audience"] = audience

    try:
        payload = jwt.decode(token, **kwargs)
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("token_expired", 401)
    except jwt.InvalidIssuerError:
        raise AuthError("invalid_issuer", 401)
    except jwt.InvalidAudienceError:
        raise AuthError("invalid_audience", 401)
    except jwt.InvalidTokenError as e:
        raise AuthError("invalid_token", 401, str(e))


def extract_roles(payload: dict) -> set[str]:
    roles: set[str] = set()

    realm_roles = payload.get("realm_access", {}).get("roles", []) or []
    roles.update(realm_roles)

    resource_access = payload.get("resource_access", {}) or {}
    for client_info in resource_access.values():
        client_roles = client_info.get("roles", []) or []
        roles.update(client_roles)

    return roles


def _authenticate_request():
    token = _get_bearer_token()
    payload = decode_and_verify(token)
    roles = extract_roles(payload)

    g.auth_token = token
    g.auth_payload = payload
    g.auth_roles = roles

    return payload, roles


def requires_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not auth_enabled():
            return fn(*args, **kwargs)

        try:
            _authenticate_request()
            return fn(*args, **kwargs)
        except AuthError as e:
            body = {"error": e.error}
            if e.details:
                body["details"] = e.details
            return jsonify(body), e.status_code

    return wrapper


def requires_roles(*required_roles: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not auth_enabled():
                return fn(*args, **kwargs)

            try:
                _, roles = _authenticate_request()
            except AuthError as e:
                body = {"error": e.error}
                if e.details:
                    body["details"] = e.details
                return jsonify(body), e.status_code

            missing = [r for r in required_roles if r not in roles]
            if missing:
                return jsonify({
                    "error": "forbidden",
                    "required_roles": list(required_roles),
                    "granted_roles": sorted(list(roles)),
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator