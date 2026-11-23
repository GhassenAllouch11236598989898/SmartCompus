"""Routes de vérification du service."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbSession

router = APIRouter()


@router.get("")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "smartcampus-backend"}


@router.get("/ready", summary="Disponibilité (API + base de données)")
def readiness(db: DbSession) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - on ne divulgue pas le détail de l'erreur
        return JSONResponse({"status": "unavailable", "database": "down"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "up"})
