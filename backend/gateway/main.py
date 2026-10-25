import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DEFAULT_ALLOWED_ORIGINS = ("http://localhost:8080", "http://127.0.0.1:8080")


def get_allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "")
    raw_origins = [item.strip() for item in configured.split(",") if item.strip()]
    if not raw_origins:
        return list(DEFAULT_ALLOWED_ORIGINS)

    origins = set()
    for origin in raw_origins:
        parsed = urlsplit(origin)
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("CORS_ALLOWED_ORIGINS must contain explicit HTTP(S) origins")
        origins.add(origin)
    return sorted(origins)

app = FastAPI(title="Sports Court Booking API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

SERVICE_URLS = {
    "user": os.getenv("USER_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/"),
    "court": os.getenv("COURT_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/"),
    "booking": os.getenv("BOOKING_SERVICE_URL", "http://127.0.0.1:8003").rstrip("/"),
    "payment": os.getenv("PAYMENT_SERVICE_URL", "http://127.0.0.1:8004").rstrip("/"),
}

PUBLIC_PREFIXES = {
    "/api/v1/auth": "user",
    "/api/v1/users": "user",
    "/api/v1/sports": "court",
    "/api/v1/venues": "court",
    "/api/v1/courts": "court",
    "/api/v1/time-slots": "court",
    "/api/v1/bookings": "booking",
    "/api/v1/payments": "payment",
}

HEALTH_PATHS = {
    "/api/v1/user/health": "user",
    "/api/v1/court/health": "court",
    "/api/v1/booking/health": "booking",
    "/api/v1/payment/health": "payment",
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
    "host",
    "content-length",
    "content-encoding",
}


@app.get("/health")
def health():
    return {"service": "gateway", "status": "ok"}


@app.api_route(
    "/api/v1/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy(path: str, request: Request):
    public_path = request.url.path
    service_name = HEALTH_PATHS.get(public_path)

    if service_name is None:
        for prefix, target_service in PUBLIC_PREFIXES.items():
            if public_path == prefix or public_path.startswith(prefix + "/"):
                service_name = target_service
                break

    if service_name is None:
        return Response(
            content='{"detail":"Not Found"}',
            status_code=404,
            media_type="application/json",
        )

    service_path = "/health" if public_path in HEALTH_PATHS else public_path
    target_url = f"{SERVICE_URLS[service_name]}{service_path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    headers = {
        name: request.headers[name]
        for name in ("authorization", "content-type", "accept")
        if name in request.headers
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            service_response = await client.request(
                method=request.method,
                url=target_url,
                content=await request.body(),
                headers=headers,
            )
    except httpx.TimeoutException:
        return Response(
            content='{"detail":"Gateway Timeout"}',
            status_code=504,
            media_type="application/json",
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Service unavailable"}',
            status_code=503,
            media_type="application/json",
        )

    response_headers = {
        name: value
        for name, value in service_response.headers.items()
        if name.lower() not in HOP_BY_HOP_HEADERS
    }
    return Response(
        content=service_response.content,
        status_code=service_response.status_code,
        headers=response_headers,
    )
