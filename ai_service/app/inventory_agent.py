import os
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

MODEL_NAME = os.getenv("MODEL_NAME", "ollama_chat/qwen2.5-coder:7b")

# "http" connects to product_mcp_server as a separate networked service
# (Docker Compose); "stdio" (default) launches it as a local subprocess
# using its own venv, for running services outside Docker.
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
MCP_HTTP_URL = os.getenv("MCP_HTTP_URL", "http://product_mcp_server:8100/mcp")

_MCP_SERVER_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "product_mcp_server")
)
_MCP_SERVER_PYTHON = os.getenv(
    "MCP_SERVER_PYTHON",
    os.path.join(_MCP_SERVER_DIR, ".venv", "bin", "python3"),
)

INSTRUCTION = """You are the HBntory inventory assistant. You answer anonymous
customers' natural-language questions about products and stock using ONLY the
tools available to you (list_products, get_product_details,
get_stock_for_product, get_stock_for_branch). Never invent product names,
descriptions, prices, or stock quantities.

You support exactly these question types:
1. Product details ("Give me details about product X").
2. Where a product is available ("Which branch has stock of product X?").
3. What products are available in a branch ("What products can I find in
   branch Y?").
4. Shopping-list recommendations ("If I want to buy N units of X, M units of
   Y, ..., which branch or branches should I visit?") — for this type ONLY,
   follow this exact procedure:
   a. Call get_stock_for_product ONCE per distinct product in the list,
      passing exactly one product_id string per call (never a list).
   b. Write down, for each product, the exact quantity returned per branch,
      copied verbatim from the tool result — never estimate or recall from
      memory.
   c. Only after every product has been checked, compare the recorded
      numbers against the requested quantities and state which branch(es)
      satisfy the full list, quoting the exact stock numbers you recorded.

If a question falls outside these types, or a tool returns an error or no
data, say so plainly instead of guessing. Do not fabricate branch names,
quantities, or product identifiers under any circumstance.
"""


def _build_toolset() -> McpToolset:
    if MCP_TRANSPORT == "http":
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_HTTP_URL,
                timeout=10.0,
            )
        )

    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_MCP_SERVER_PYTHON,
                args=["-m", "app.server"],
                cwd=_MCP_SERVER_DIR,
                env={
                    "PRODUCT_API_BASE_URL": os.getenv(
                        "PRODUCT_API_BASE_URL", "http://localhost:5001"
                    ),
                    "STOCK_DATABASE_URL": os.getenv(
                        "STOCK_DATABASE_URL",
                        "postgresql+psycopg2://hbntory:hbntory@localhost:5432/hbntory",
                    ),
                    "PATH": os.environ.get("PATH", ""),
                },
            ),
            timeout=10.0,
        )
    )


def build_agent() -> Agent:
    toolset = _build_toolset()

    return Agent(
        name="inventory_assistant",
        model=MODEL_NAME,
        instruction=INSTRUCTION,
        tools=[toolset],
    )
