import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.registry import ServiceRegistry


DOWNSTREAM_PATHS = {
    "members": "/members",
    "trainers": "/trainers",
    "classes": "/classes",
    "equipment": "/equipment",
}

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}

RESPONSE_EXCLUDED_HEADERS = HOP_BY_HOP_HEADERS | {"content-length", "content-encoding"}
REQUEST_EXCLUDED_HEADERS = HOP_BY_HOP_HEADERS | {"host", "content-length"}


def _build_forward_headers(request: Request) -> dict[str, str]:
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in REQUEST_EXCLUDED_HEADERS
    }

    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    client_host = request.client.host if request.client else ""
    headers["X-Forwarded-For"] = ", ".join(
        value for value in [forwarded_for, client_host] if value
    )
    headers["X-Forwarded-Proto"] = request.url.scheme

    host_header = request.headers.get("host")
    if host_header:
        headers["X-Forwarded-Host"] = host_header

    return headers


def _build_response_headers(headers: httpx.Headers) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if name.lower() not in RESPONSE_EXCLUDED_HEADERS
    }


async def proxy_request(
    request: Request,
    service_name: str,
    subpath: str,
    registry: ServiceRegistry,
    client: httpx.AsyncClient,
) -> Response:
    downstream_prefix = DOWNSTREAM_PATHS[service_name]
    downstream_path = downstream_prefix if not subpath else f"{downstream_prefix}/{subpath}"
    target_url = registry.build_url(service_name, downstream_path)

    try:
        upstream_response = await client.request(
            method=request.method,
            url=target_url,
            params=list(request.query_params.multi_items()),
            headers=_build_forward_headers(request),
            content=await request.body(),
        )
    except httpx.TimeoutException as exc:
        return JSONResponse(
            status_code=504,
            content={
                "error": "upstream_timeout",
                "service": service_name,
                "details": str(exc),
            },
        )
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "error": "upstream_unavailable",
                "service": service_name,
                "details": str(exc),
            },
        )

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=_build_response_headers(upstream_response.headers),
    )
