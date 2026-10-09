"""Domain-level service errors.

Routes stay thin: services raise these, and FastAPI exception handlers
(registered in main.py) map them to HTTP responses.
"""


class NotFoundError(Exception):
    """Requested entity does not exist (HTTP 404)."""


class AccessDeniedError(Exception):
    """Entity exists but the acting user may not access it (HTTP 403)."""


class ConflictError(Exception):
    """Operation conflicts with current state (HTTP 409)."""


class ValidationError(Exception):
    """Semantically invalid request despite passing schema checks (HTTP 422)."""
