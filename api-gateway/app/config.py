import os
from dataclasses import dataclass
from functools import lru_cache


DEFAULT_SERVICE_URLS = {
    "members": "http://members-service:8001",
    "trainers": "http://trainers-service:8002",
    "classes": "http://classes-service:8003",
    "equipment": "http://equipment-service:8004",
}

SERVICE_ENV_VARS = {
    "members": "MEMBERS_SERVICE_URLS",
    "trainers": "TRAINERS_SERVICE_URLS",
    "classes": "CLASSES_SERVICE_URLS",
    "equipment": "EQUIPMENT_SERVICE_URLS",
}


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: str) -> int:
    try:
        return int(os.getenv(name, default).strip())
    except (AttributeError, ValueError):
        return int(default)


def _env_float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default).strip())
    except (AttributeError, ValueError):
        return float(default)


def _parse_service_urls(raw_value: str) -> list[str]:
    return [
        url.strip().rstrip("/")
        for url in raw_value.split(",")
        if url.strip()
    ]


@dataclass(frozen=True, slots=True)
class Settings:
    auth_enabled: bool
    oidc_issuer: str
    oidc_jwks_url: str
    oidc_verify_iss: bool
    oidc_verify_aud: bool
    oidc_audience: str
    request_timeout_seconds: float
    dashboard_preview_size: int
    service_urls: dict[str, list[str]]


@lru_cache
def get_settings() -> Settings:
    service_urls = {
        service_name: _parse_service_urls(
            os.getenv(env_name, DEFAULT_SERVICE_URLS[service_name])
        )
        for service_name, env_name in SERVICE_ENV_VARS.items()
    }

    missing_urls = [
        service_name
        for service_name, urls in service_urls.items()
        if not urls
    ]
    if missing_urls:
        joined = ", ".join(sorted(missing_urls))
        raise ValueError(f"Missing service URLs for: {joined}")

    return Settings(
        auth_enabled=_env_bool("AUTH_ENABLED", "1"),
        oidc_issuer=os.getenv("OIDC_ISSUER", "").strip(),
        oidc_jwks_url=os.getenv("OIDC_JWKS_URL", "").strip(),
        oidc_verify_iss=_env_bool("OIDC_VERIFY_ISS", "1"),
        oidc_verify_aud=_env_bool("OIDC_VERIFY_AUD", "0"),
        oidc_audience=os.getenv("OIDC_AUDIENCE", "").strip(),
        request_timeout_seconds=_env_float("REQUEST_TIMEOUT_SECONDS", "10"),
        dashboard_preview_size=_env_int("DASHBOARD_PREVIEW_SIZE", "3"),
        service_urls=service_urls,
    )
