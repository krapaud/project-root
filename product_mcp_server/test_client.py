"""Manual test script: exercises every tool exposed by the Product MCP server.

Run with: python test_client.py
"""

import asyncio

from fastmcp import Client

from app.server import mcp


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("Available tools:", [t.name for t in tools])

        print("\n--- list_products() ---")
        result = await client.call_tool("list_products", {})
        print(result.data)

        print("\n--- get_product_details('prod-001') [valid] ---")
        result = await client.call_tool("get_product_details", {"product_id": "prod-001"})
        print(result.data)

        print("\n--- get_product_details('does-not-exist') [invalid id] ---")
        result = await client.call_tool("get_product_details", {"product_id": "does-not-exist"})
        print(result.data)

        print("\n--- get_stock_for_product('prod-001') ---")
        result = await client.call_tool("get_stock_for_product", {"product_id": "prod-001"})
        print(result.data)

        print("\n--- get_stock_for_branch(1) ---")
        result = await client.call_tool("get_stock_for_branch", {"branch_id": 1})
        print(result.data)

        print("\n--- get_stock_for_branch(999) [no stock] ---")
        result = await client.call_tool("get_stock_for_branch", {"branch_id": 999})
        print(result.data)


if __name__ == "__main__":
    asyncio.run(main())
