"""Route de vérification du service."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "smartcampus-backend"}
