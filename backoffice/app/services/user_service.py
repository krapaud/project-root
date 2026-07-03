from sqlalchemy.orm import Session

from app.models import Branch, User, UserRole
from app.security import hash_password


class UserValidationError(Exception):
    """Raised when a user management operation violates a business rule."""


def _get_branch_or_raise(db: Session, branch_id: int) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise UserValidationError(f"Branch {branch_id} does not exist.")
    return branch


def list_users(db: Session) -> list[User]:
    return list(db.query(User).order_by(User.username).all())


def create_common_user(db: Session, username: str, password: str, branch_id: int) -> User:
    if not username or not password:
        raise UserValidationError("Username and password are required.")
    if db.query(User).filter_by(username=username).one_or_none() is not None:
        raise UserValidationError(f"Username '{username}' is already taken.")

    _get_branch_or_raise(db, branch_id)

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=UserRole.COMMON,
        branch_id=branch_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_common_user_or_raise(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserValidationError(f"User {user_id} does not exist.")
    if user.role != UserRole.COMMON:
        raise UserValidationError("Admin users cannot be managed through this operation.")
    return user


def change_branch(db: Session, user_id: int, branch_id: int) -> User:
    user = _get_common_user_or_raise(db, user_id)
    _get_branch_or_raise(db, branch_id)
    user.branch_id = branch_id
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user_id: int, new_password: str) -> User:
    if not new_password:
        raise UserValidationError("Password cannot be empty.")
    user = _get_common_user_or_raise(db, user_id)
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user_id: int) -> User:
    user = _get_common_user_or_raise(db, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user
