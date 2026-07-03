from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import verify_password

SESSION_USER_ID_KEY = "user_id"


class NotAuthenticatedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter_by(username=username).one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def log_in(request: Request, user: User) -> None:
    request.session[SESSION_USER_ID_KEY] = user.id


def log_out(request: Request) -> None:
    request.session.pop(SESSION_USER_ID_KEY, None)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get(SESSION_USER_ID_KEY)
    if user_id is None:
        raise NotAuthenticatedError()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        request.session.pop(SESSION_USER_ID_KEY, None)
        raise NotAuthenticatedError()

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


def require_common_user(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.COMMON:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to branch staff.",
        )
    return user
