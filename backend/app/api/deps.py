"""API dependencies.

⚠️  DEVELOPMENT-ONLY IDENTITY ==========================================

`get_current_user` identifies the user from the `X-Demo-User-ID` HTTP
header (auto-seeded as id 1). Development-only, NO security; all routes
depend on this single function so real auth is a one-file swap.

=========================================================================
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User


def get_current_user(
    x_demo_user_id: int | None = Header(
        default=None,
        alias="X-Demo-User-ID",
        description="DEVELOPMENT-ONLY user identification.",
    ),
    db: Session = Depends(get_db),
) -> User:
    if x_demo_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Demo-User-ID header (development-only identity).",
        )
    user = db.get(User, x_demo_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unknown user id.",
        )
    return user
