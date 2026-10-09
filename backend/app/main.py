"""Iron Log API — gym workout tracker backend."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import exercises, health, misc, workouts
from app.services.errors import ConflictError, NotFoundError, ValidationError

app = FastAPI(
    title="Iron Log API",
    version="0.1.0",
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(exercises.router, prefix="/api/v1")
app.include_router(workouts.router, prefix="/api/v1")
app.include_router(misc.router, prefix="/api/v1")


# ---- domain error -> HTTP mapping (no stack traces leaked) ----


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# Last-resort safety net: log server-side, return a generic message.
@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
