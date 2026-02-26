"""HatiData Agent SDK — Sub-10ms SQL for AI agents.

Provides agent-aware database access to HatiData's in-VPC data warehouse
via the Postgres wire protocol. Agents identify themselves through startup
parameters, enabling per-agent billing, scheduling, and audit trails.

Quick start::

    from hatidata_agent import HatiDataAgent

    agent = HatiDataAgent(
        host="localhost",
        port=5439,
        agent_id="my-agent",
        framework="langchain",
    )
    rows = agent.query("SELECT * FROM customers WHERE status = 'active' LIMIT 10")
"""

from hatidata_agent.client import HatiDataAgent
from hatidata_agent.control_plane import ControlPlaneClient
from hatidata_agent.local_engine import LocalDuckDBEngine

__version__ = "0.3.1"
__all__ = ["HatiDataAgent", "ControlPlaneClient", "LocalDuckDBEngine"]
