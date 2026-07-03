import os

from sqlalchemy import create_engine, text

STOCK_DATABASE_URL = os.getenv("STOCK_DATABASE_URL", "sqlite:///../backoffice/backoffice.db")

_connect_args = {"check_same_thread": False} if STOCK_DATABASE_URL.startswith("sqlite") else {}
_engine = create_engine(STOCK_DATABASE_URL, connect_args=_connect_args)


class StockQueryError(Exception):
    """The stock database could not be reached or queried."""


def get_stock_for_product(product_id: str) -> list[dict]:
    query = text(
        "SELECT s.branch_id, b.name AS branch_name, s.quantity "
        "FROM stock s JOIN branches b ON b.id = s.branch_id "
        "WHERE s.product_id = :product_id"
    )
    try:
        with _engine.connect() as conn:
            rows = conn.execute(query, {"product_id": product_id}).mappings().all()
    except Exception as exc:
        raise StockQueryError(f"Could not query stock database: {exc}") from exc

    return [dict(row) for row in rows]


def get_stock_for_branch(branch_id: int) -> list[dict]:
    query = text(
        "SELECT product_id, quantity FROM stock WHERE branch_id = :branch_id"
    )
    try:
        with _engine.connect() as conn:
            rows = conn.execute(query, {"branch_id": branch_id}).mappings().all()
    except Exception as exc:
        raise StockQueryError(f"Could not query stock database: {exc}") from exc

    return [dict(row) for row in rows]
