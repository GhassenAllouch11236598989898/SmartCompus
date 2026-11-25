"""Format d'erreur JSON uniforme :

    {"error": {"code": "not_found", "message": "...", "details": [...] | null}}
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("smartcampus.errors")

_STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "too_many_requests",
    503: "service_unavailable",
}


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, details: Any = None, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code, code = 404, "not_found"


class UnauthorizedError(AppError):
    status_code, code = 401, "unauthorized"


class ForbiddenError(AppError):
    status_code, code = 403, "forbidden"


class ConflictError(AppError):
    status_code, code = 409, "conflict"


class UnprocessableError(AppError):
    status_code, code = 422, "validation_error"


class ServiceUnavailableError(AppError):
    status_code, code = 503, "service_unavailable"


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def _clean_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # On ne renvoie pas "input" (pourrait contenir des données personnelles) ni "url".
    return [
        {"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
        for e in errors
    ]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(error_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            error_body("validation_error", "Requête invalide.", _clean_validation_errors(exc.errors())),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else code
        if exc.status_code == 404 and message == "Not Found":
            message = "Ressource introuvable."
        if exc.status_code == 400 and message.startswith("There was an error parsing the body"):
            message = "Corps de requête JSON invalide (vérifier la syntaxe et l'encodage UTF-8)."
        if exc.status_code == 405:
            message = "Méthode non autorisée (les formations s'archivent, elles ne se suppriment pas)."
        return JSONResponse(error_body(code, message), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - filet de sécurité
        logger.exception("Erreur interne non gérée: %s", type(exc).__name__)
        return JSONResponse(error_body("internal_error", "Erreur interne du serveur."), status_code=500)
