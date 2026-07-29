from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.logger import get_logger
from app.shared.exceptions import AppException
from app.shared.responses import error_response

logger = get_logger(__name__)

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "%s %s -> %s",
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(status_code=exc.status_code, content=error_response(message=exc.message).model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception while processing %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(status_code=500, content=error_response(message="Internal server error.").model_dump())