import os

import httpx

PRODUCT_API_BASE_URL = os.getenv("PRODUCT_API_BASE_URL", "http://localhost:8080")


class ProductAPIError(Exception):
    """The Product API could not be reached or returned an unexpected error."""


class ProductNotFoundError(Exception):
    """The requested product id does not exist in the Product API."""


def list_products() -> list[dict]:
    try:
        response = httpx.get(f"{PRODUCT_API_BASE_URL}/products", timeout=5.0)
    except httpx.RequestError as exc:
        raise ProductAPIError(f"Could not reach Product API: {exc}") from exc

    if response.status_code >= 400:
        raise ProductAPIError(f"Product API returned status {response.status_code}")

    return response.json()


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
