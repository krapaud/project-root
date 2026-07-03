from fastmcp import FastMCP

from app.product_api_client import ProductAPIError, ProductNotFoundError
from app.product_api_client import get_product as _get_product
from app.product_api_client import list_products as _list_products
from app.stock_client import StockQueryError
from app.stock_client import get_stock_for_branch as _get_stock_for_branch
from app.stock_client import get_stock_for_product as _get_stock_for_product

mcp = FastMCP("HBntory Product MCP Server")


@mcp.tool()
def list_products() -> list[dict]:
    """List all available products from the external Product API."""
    try:
        return _list_products()
    except ProductAPIError as exc:
        return [{"error": str(exc)}]


@mcp.tool()
def get_product_details(product_id: str) -> dict:
    """Get full details for one product by its identifier."""
    try:
        return _get_product(product_id)
    except ProductNotFoundError as exc:
        return {"error": str(exc)}
    except ProductAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_stock_for_product(product_id: str) -> dict:
    """Get stock quantities for one product across all branches."""
    try:
        rows = _get_stock_for_product(product_id)
    except StockQueryError as exc:
        return {"error": str(exc)}

    if not rows:
        return {"product_id": product_id, "branches": [], "note": "No stock recorded for this product."}
    return {"product_id": product_id, "branches": rows}


@mcp.tool()
def get_stock_for_branch(branch_id: int) -> dict:
    """Get stock quantities for every product held in one branch."""
    try:
        rows = _get_stock_for_branch(branch_id)
    except StockQueryError as exc:
        return {"error": str(exc)}

    if not rows:
        return {"branch_id": branch_id, "products": [], "note": "No stock recorded for this branch."}
    return {"branch_id": branch_id, "products": rows}


if __name__ == "__main__":
    mcp.run()
