import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, Request

from app.registry import ServiceRegistry


COLLECTION_PATHS = {
    "members": "/members",
    "trainers": "/trainers",
    "classes": "/classes",
    "equipment": "/equipment",
}


def _downstream_headers(request: Request) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


def _extract_error_payload(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


async def _fetch_collection(
    request: Request,
    service_name: str,
    registry: ServiceRegistry,
    client: httpx.AsyncClient,
) -> list[dict]:
    target_url = registry.build_url(service_name, COLLECTION_PATHS[service_name])

    try:
        response = await client.get(
            target_url,
            headers=_downstream_headers(request),
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "upstream_timeout",
                "service": service_name,
                "details": str(exc),
            },
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "upstream_unavailable",
                "service": service_name,
                "details": str(exc),
            },
        ) from exc

    if response.status_code == 200:
        payload = response.json()
        if not isinstance(payload, list):
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "invalid_upstream_payload",
                    "service": service_name,
                },
            )
        return payload

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "error": "upstream_authorization_failed",
                "service": service_name,
                "payload": _extract_error_payload(response),
            },
        )

    raise HTTPException(
        status_code=502,
        detail={
            "error": "upstream_request_failed",
            "service": service_name,
            "status_code": response.status_code,
            "payload": _extract_error_payload(response),
        },
    )


async def build_dashboard_summary(
    request: Request,
    registry: ServiceRegistry,
    client: httpx.AsyncClient,
    preview_size: int,
) -> dict:
    members, trainers, classes, equipment = await asyncio.gather(
        _fetch_collection(request, "members", registry, client),
        _fetch_collection(request, "trainers", registry, client),
        _fetch_collection(request, "classes", registry, client),
        _fetch_collection(request, "equipment", registry, client),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {
            "members": len(members),
            "trainers": len(trainers),
            "classes": len(classes),
            "equipment": len(equipment),
        },
        "highlights": {
            "classes": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "schedule": item.get("schedule"),
                    "max_capacity": item.get("max_capacity"),
                    "trainer_id": item.get("trainer_id"),
                }
                for item in classes[:preview_size]
            ],
            "trainers": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "specialty": item.get("specialty"),
                }
                for item in trainers[:preview_size]
            ],
        },
    }
