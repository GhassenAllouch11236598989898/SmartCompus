"""Point d'entrée HTTP du backend SmartCampus AI."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers

logger = logging.getLogger("smartcampus.access")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description=(
            "API SmartCampus AI — epic SA-10 : catalogue des formations, tarifs officiels et conditions "
            "d'admission. Toutes les informations du catalogue sont traçables jusqu'à leur document source. "
            "Les routes d'écriture exigent un JWT (rôle admin ou responsable de l'établissement)."
        ),
        version="0.2.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Response-Time-ms"],
    )

    @app.middleware("http")
    async def response_time(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-ms"] = f"{elapsed_ms:.1f}"
        # Aucun en-tête, corps ni paramètre de requête n'est journalisé (pas de secret dans les logs).
        logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
        return response

    register_error_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/", tags=["System"])
    def home() -> dict[str, str]:
        return {"service": "SmartCampus AI API", "docs": "/docs"}

    return app


app = create_app()
