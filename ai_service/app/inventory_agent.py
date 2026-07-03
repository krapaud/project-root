import os
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

MODEL_NAME = os.getenv("MODEL_NAME", "ollama_chat/qwen2.5-coder:7b")

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
   Y, ..., which branch or branches should I visit?") — check
   get_stock_for_product for each item and reason about which branch(es)
   can satisfy the full list, or which items are missing where.

If a question falls outside these types, or a tool returns an error or no
data, say so plainly instead of guessing. Do not fabricate branch names,
quantities, or product identifiers under any circumstance.
"""


def build_agent() -> Agent:
    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=_MCP_SERVER_PYTHON,
                args=["-m", "app.server"],
                cwd=_MCP_SERVER_DIR,
                env={
                    "PRODUCT_API_BASE_URL": os.getenv(
                        "PRODUCT_API_BASE_URL", "http://localhost:8080"
                    ),
                    "STOCK_DATABASE_URL": os.getenv(
                        "STOCK_DATABASE_URL", "sqlite:///../backoffice/backoffice.db"
                    ),
                    "PATH": os.environ.get("PATH", ""),
                },
            ),
            timeout=10.0,
        )
    )

    return Agent(
        name="inventory_assistant",
        model=MODEL_NAME,
        instruction=INSTRUCTION,
        tools=[toolset],
    )
