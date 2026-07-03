from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import authenticate_user, get_current_user, log_in, log_out
from app.database import get_db
from app.models import User, UserRole

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if user is None:
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password."}, status_code=401
        )

    log_in(request, user)
    destination = "/admin/users" if user.role == UserRole.ADMIN else "/stock"
    return RedirectResponse(url=destination, status_code=303)


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user)):
    log_out(request)
    return RedirectResponse(url="/login", status_code=303)
