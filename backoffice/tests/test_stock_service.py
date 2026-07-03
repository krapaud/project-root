from unittest.mock import patch

import pytest

from app.services.stock_service import (
    StockValidationError,
    add_stock,
    list_branch_stock,
    remove_stock,
)


@pytest.fixture(autouse=True)
def mock_product_api():
    with patch("app.services.stock_service.get_product") as mock_get_product:
        mock_get_product.side_effect = lambda pid: (
            {"id": pid, "name": "Widget"} if pid == "prod-001" else _raise_not_found(pid)
        )
        yield mock_get_product


def _raise_not_found(product_id):
    from app.product_api_client import ProductNotFoundError

    raise ProductNotFoundError(f"No product found with id '{product_id}'")


def test_common_user_adds_valid_stock(db, downtown):
    stock = add_stock(db, downtown.id, "prod-001", 10)
    assert stock.quantity == 10


def test_common_user_removes_valid_stock(db, downtown):
    add_stock(db, downtown.id, "prod-001", 10)
    stock = remove_stock(db, downtown.id, "prod-001", 4)
    assert stock.quantity == 6


def test_common_user_cannot_remove_more_stock_than_available(db, downtown):
    add_stock(db, downtown.id, "prod-001", 10)
    with pytest.raises(StockValidationError, match="only 10 available"):
        remove_stock(db, downtown.id, "prod-001", 11)


def test_stock_quantity_never_goes_negative(db, downtown):
    add_stock(db, downtown.id, "prod-001", 5)
    with pytest.raises(StockValidationError):
        remove_stock(db, downtown.id, "prod-001", 999)

    stock = list_branch_stock(db, downtown.id)[0]
    assert stock.quantity == 5


def test_add_stock_rejects_zero_or_negative_quantity(db, downtown):
    with pytest.raises(StockValidationError):
        add_stock(db, downtown.id, "prod-001", 0)
    with pytest.raises(StockValidationError):
        add_stock(db, downtown.id, "prod-001", -3)


def test_add_stock_rejects_unknown_product(db, downtown):
    with pytest.raises(StockValidationError, match="No product found"):
        add_stock(db, downtown.id, "does-not-exist", 5)


def test_stock_operation_rejects_invalid_branch(db):
    with pytest.raises(StockValidationError, match="does not exist"):
        add_stock(db, 999, "prod-001", 5)


def test_list_branch_stock_isolated_per_branch(db, downtown, airport):
    add_stock(db, downtown.id, "prod-001", 10)
    assert len(list_branch_stock(db, downtown.id)) == 1
    assert list_branch_stock(db, airport.id) == []
