import os

import httpx

PRODUCT_API_BASE_URL = os.getenv("PRODUCT_API_BASE_URL", "http://localhost:8080")


class ProductAPIError(Exception):
    """Raised when the external Product API is unreachable or errors out."""


class ProductNotFoundError(Exception):
    """Raised when a product id does not exist in the external Product API."""


def get_product(product_id: str) -> dict:
    try:
        response = httpx.get(f"{PRODUCT_API_BASE_URL}/products/{product_id}", timeout=5.0)
    except httpx.RequestError as exc:
        raise ProductAPIError(f"Could not reach Product API: {exc}") from exc

    if response.status_code == 404:
        raise ProductNotFoundError(f"No product found with id '{product_id}'")
    if response.status_code >= 400:
        raise ProductAPIError(f"Product API returned status {response.status_code}")

    return response.json()


def list_products() -> list[dict]:
    try:
        response = httpx.get(f"{PRODUCT_API_BASE_URL}/products", timeout=5.0)
    except httpx.RequestError as exc:
        raise ProductAPIError(f"Could not reach Product API: {exc}") from exc

    if response.status_code >= 400:
        raise ProductAPIError(f"Product API returned status {response.status_code}")

    return response.json()
