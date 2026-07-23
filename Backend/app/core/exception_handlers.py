from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.shared.exceptions import AppException
from app.shared.responses import error_response

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=exc.message,
            ).model_dump(),
        )