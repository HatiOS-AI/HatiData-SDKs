"""CrewAI integration for HatiData.

Provides Memory and Tool implementations that let CrewAI agents
query, explore, and persist data in HatiData's in-VPC warehouse.

Usage::

    from crewai import Agent, Task, Crew
    from crewai_hatidata import HatiDataQueryTool, HatiDataMemory

    query_tool = HatiDataQueryTool(host="proxy.internal", agent_id="analyst")
    memory = HatiDataMemory(host="proxy.internal", agent_id="analyst")

    agent = Agent(
        role="Data Analyst",
        tools=[query_tool],
        memory=memory,
    )
"""

from crewai_hatidata.memory import HatiDataMemory
from crewai_hatidata.tools import (
    HatiDataQueryTool,
    HatiDataListTablesTool,
    HatiDataDescribeTableTool,
    HatiDataContextSearchTool,
)

__version__ = "0.1.0"
__all__ = [
    "HatiDataMemory",
    "HatiDataQueryTool",
    "HatiDataListTablesTool",
    "HatiDataDescribeTableTool",
    "HatiDataContextSearchTool",
]
