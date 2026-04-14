from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.aggregator import build_dashboard_summary
from app.config import get_settings
from app.proxy import proxy_request
from app.registry import ServiceRegistry
from app.security import AuthError, authenticate_request


ALL_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

    app.state.settings = settings
    app.state.registry = ServiceRegistry(settings.service_urls)

    async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=False) as client:
        app.state.http_client = client
        yield


app = FastAPI(
    title="Gym API Gateway",
    version="1.0.0",
    description="Gateway centralizado para routing, seguridad y agregacion del sistema de gimnasio.",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    settings = request.app.state.settings
    client = request.app.state.http_client

    try:
        await authenticate_request(request, client, settings)
    except AuthError as exc:
        body = {"error": exc.error}
        if exc.details:
            body["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=body)

    return await call_next(request)


@app.get("/health", tags=["Gateway"])
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.get("/api/dashboard/summary", tags=["Dashboard"])
async def dashboard_summary(request: Request):
    settings = request.app.state.settings
    registry = request.app.state.registry
    client = request.app.state.http_client

    return await build_dashboard_summary(
        request=request,
        registry=registry,
        client=client,
        preview_size=settings.dashboard_preview_size,
    )


@app.api_route("/api/members", methods=ALL_PROXY_METHODS, tags=["Members Proxy"])
@app.api_route("/api/members/{path:path}", methods=ALL_PROXY_METHODS, tags=["Members Proxy"])
async def members_proxy(request: Request, path: str = ""):
    return await proxy_request(
        request=request,
        service_name="members",
        subpath=path,
        registry=request.app.state.registry,
        client=request.app.state.http_client,
    )


@app.api_route("/api/trainers", methods=ALL_PROXY_METHODS, tags=["Trainers Proxy"])
@app.api_route("/api/trainers/{path:path}", methods=ALL_PROXY_METHODS, tags=["Trainers Proxy"])
async def trainers_proxy(request: Request, path: str = ""):
    return await proxy_request(
        request=request,
        service_name="trainers",
        subpath=path,
        registry=request.app.state.registry,
        client=request.app.state.http_client,
    )


@app.api_route("/api/classes", methods=ALL_PROXY_METHODS, tags=["Classes Proxy"])
@app.api_route("/api/classes/{path:path}", methods=ALL_PROXY_METHODS, tags=["Classes Proxy"])
async def classes_proxy(request: Request, path: str = ""):
    return await proxy_request(
        request=request,
        service_name="classes",
        subpath=path,
        registry=request.app.state.registry,
        client=request.app.state.http_client,
    )


@app.api_route("/api/equipment", methods=ALL_PROXY_METHODS, tags=["Equipment Proxy"])
@app.api_route("/api/equipment/{path:path}", methods=ALL_PROXY_METHODS, tags=["Equipment Proxy"])
async def equipment_proxy(request: Request, path: str = ""):
    return await proxy_request(
        request=request,
        service_name="equipment",
        subpath=path,
        registry=request.app.state.registry,
        client=request.app.state.http_client,
    )
