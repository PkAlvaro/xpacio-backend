import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError

logger = structlog.get_logger()


class DomainException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(DomainException):
    def __init__(self, resource: str):
        super().__init__(f"{resource} no encontrado", status_code=404)


class ForbiddenError(DomainException):
    def __init__(self, message: str = "Acceso denegado"):
        super().__init__(message, status_code=403)


class ConflictError(DomainException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


def _error_response(status_code: int, message: str, detail=None) -> JSONResponse:
    body = {"success": False, "data": None, "error": message}
    if detail:
        body["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    return _error_response(exc.status_code, exc.message)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return _error_response(422, "Error de validación", detail=errors)


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("db_integrity_error", error=str(exc.orig))
    return _error_response(409, "Conflicto de datos — el recurso ya existe o viola una restricción")


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", exc_info=exc)
    return _error_response(500, "Error interno del servidor")
