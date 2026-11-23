"""Point d'entrée HTTP du backend SmartCampus AI."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as api_v1_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="SmartCampus AI API",
        description="Backend initial de la plateforme SmartCampus AI.",
        version="0.1.0",
    )
    # En développement : autoriser uniquement les origines configurées.
    origins = [url.strip() for url in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if url.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/", tags=["System"])
    def home() -> dict[str, str]:
        return {"service": "SmartCampus AI API", "docs": "/docs"}

    return app


app = create_app()
