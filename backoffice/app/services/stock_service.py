from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branch, Stock
from app.product_api_client import ProductAPIError, ProductNotFoundError, get_product


class StockValidationError(Exception):
    """Raised when a stock operation violates a business rule."""


def _get_branch_or_raise(db: Session, branch_id: int) -> Branch:
    branch = db.get(Branch, branch_id)
    if branch is None:
        raise StockValidationError(f"Branch {branch_id} does not exist.")
    return branch


def _validate_product_exists(product_id: str) -> None:
    try:
        get_product(product_id)
    except ProductNotFoundError as exc:
        raise StockValidationError(str(exc)) from exc
    except ProductAPIError as exc:
        raise StockValidationError(
            f"Cannot validate product '{product_id}': {exc}"
        ) from exc


def _validate_quantity(quantity: int) -> None:
    if not isinstance(quantity, int) or isinstance(quantity, bool):
        raise StockValidationError("Quantity must be an integer.")
    if quantity <= 0:
        raise StockValidationError("Quantity must be a positive integer.")


def get_stock_row(db: Session, branch_id: int, product_id: str) -> Stock | None:
    stmt = select(Stock).where(Stock.branch_id == branch_id, Stock.product_id == product_id)
    return db.execute(stmt).scalar_one_or_none()


def add_stock(db: Session, branch_id: int, product_id: str, quantity: int) -> Stock:
    _validate_quantity(quantity)
    _get_branch_or_raise(db, branch_id)
    _validate_product_exists(product_id)

    stock = get_stock_row(db, branch_id, product_id)
    if stock is None:
        stock = Stock(branch_id=branch_id, product_id=product_id, quantity=0)
        db.add(stock)

    stock.quantity += quantity
    db.commit()
    db.refresh(stock)
    return stock


def remove_stock(db: Session, branch_id: int, product_id: str, quantity: int) -> Stock:
    _validate_quantity(quantity)
    _get_branch_or_raise(db, branch_id)

    stock = get_stock_row(db, branch_id, product_id)
    if stock is None or stock.quantity < quantity:
        available = stock.quantity if stock else 0
        raise StockValidationError(
            f"Cannot remove {quantity} unit(s): only {available} available "
            f"for product '{product_id}' in branch {branch_id}."
        )

    stock.quantity -= quantity
    db.commit()
    db.refresh(stock)
    return stock


def list_branch_stock(db: Session, branch_id: int) -> list[Stock]:
    _get_branch_or_raise(db, branch_id)
    stmt = select(Stock).where(Stock.branch_id == branch_id)
    return list(db.execute(stmt).scalars().all())
