from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import require_common_user
from app.database import get_db
from app.models import User
from app.services.stock_service import (
    StockValidationError,
    add_stock,
    list_branch_stock,
    remove_stock,
)

router = APIRouter(prefix="/stock", tags=["stock"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def view_branch_stock(
    request: Request,
    user: User = Depends(require_common_user),
    db: Session = Depends(get_db),
):
    stock_items = list_branch_stock(db, user.branch_id)
    return templates.TemplateResponse(
        request,
        "stock.html",
        {"user": user, "branch": user.branch, "stock_items": stock_items, "error": None},
    )


@router.post("/add", response_class=HTMLResponse)
def add_stock_route(
    request: Request,
    product_id: str = Form(...),
    quantity: int = Form(...),
    user: User = Depends(require_common_user),
    db: Session = Depends(get_db),
):
    error = None
    try:
        add_stock(db, user.branch_id, product_id, quantity)
    except StockValidationError as exc:
        error = str(exc)

    stock_items = list_branch_stock(db, user.branch_id)
    return templates.TemplateResponse(
        request,
        "stock.html",
        {"user": user, "branch": user.branch, "stock_items": stock_items, "error": error},
    )


@router.post("/remove", response_class=HTMLResponse)
def remove_stock_route(
    request: Request,
    product_id: str = Form(...),
    quantity: int = Form(...),
    user: User = Depends(require_common_user),
    db: Session = Depends(get_db),
):
    error = None
    try:
        remove_stock(db, user.branch_id, product_id, quantity)
    except StockValidationError as exc:
        error = str(exc)

    stock_items = list_branch_stock(db, user.branch_id)
    return templates.TemplateResponse(
        request,
        "stock.html",
        {"user": user, "branch": user.branch, "stock_items": stock_items, "error": error},
    )
