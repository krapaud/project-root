from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import Branch, User
from app.services.user_service import (
    UserValidationError,
    change_branch,
    change_password,
    create_common_user,
    list_users,
    soft_delete_user,
)

router = APIRouter(prefix="/admin/users", tags=["users"])
templates = Jinja2Templates(directory="app/templates")


def _render(request: Request, admin: User, db: Session, error: str | None = None, message: str | None = None):
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {
            "admin": admin,
            "users": list_users(db),
            "branches": db.query(Branch).order_by(Branch.name).all(),
            "error": error,
            "message": message,
        },
    )


@router.get("", response_class=HTMLResponse)
def list_users_page(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return _render(request, admin, db)


@router.post("/create", response_class=HTMLResponse)
def create_user_route(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    branch_id: int = Form(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        create_common_user(db, username, password, branch_id)
        return _render(request, admin, db, message=f"User '{username}' created.")
    except UserValidationError as exc:
        return _render(request, admin, db, error=str(exc))


@router.post("/{user_id}/branch", response_class=HTMLResponse)
def change_branch_route(
    request: Request,
    user_id: int,
    branch_id: int = Form(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        change_branch(db, user_id, branch_id)
        return _render(request, admin, db, message="Branch updated.")
    except UserValidationError as exc:
        return _render(request, admin, db, error=str(exc))


@router.post("/{user_id}/password", response_class=HTMLResponse)
def change_password_route(
    request: Request,
    user_id: int,
    new_password: str = Form(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        change_password(db, user_id, new_password)
        return _render(request, admin, db, message="Password updated.")
    except UserValidationError as exc:
        return _render(request, admin, db, error=str(exc))


@router.post("/{user_id}/delete", response_class=HTMLResponse)
def soft_delete_user_route(
    request: Request,
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        soft_delete_user(db, user_id)
        return _render(request, admin, db, message="User deactivated.")
    except UserValidationError as exc:
        return _render(request, admin, db, error=str(exc))
