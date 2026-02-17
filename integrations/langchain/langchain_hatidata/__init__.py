"""LangChain integration for HatiData.

Provides Memory, VectorStore, and Tool implementations backed by HatiData's
in-VPC data warehouse with agent-aware billing and audit.

Usage::

    from langchain_hatidata import HatiDataMemory, HatiDataVectorStore, HatiDataToolkit

    # Conversation memory persisted to HatiData
    memory = HatiDataMemory(host="proxy.internal", agent_id="my-agent")

    # Vector store for RAG
    vectorstore = HatiDataVectorStore(host="proxy.internal", agent_id="my-agent", table="embeddings")

    # SQL tools for agents
    toolkit = HatiDataToolkit(host="proxy.internal", agent_id="my-agent")
"""

from langchain_hatidata.memory import HatiDataMemory
from langchain_hatidata.vectorstore import HatiDataVectorStore
from langchain_hatidata.tools import HatiDataToolkit

__version__ = "0.1.1"
__all__ = ["HatiDataMemory", "HatiDataVectorStore", "HatiDataToolkit"]
