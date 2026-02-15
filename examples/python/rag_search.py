"""HatiData RAG Context Retrieval

Prerequisites:
    pip install hatidata-agent

Usage:
    python rag_search.py
"""

from hatidata_agent import HatiDataAgent


def main():
    agent = HatiDataAgent(
        host="localhost",
        port=5439,
        agent_id="rag-example",
    )

    # Full-text search: find relevant context by keyword
    print("=== Full-Text Search ===")
    context = agent.get_context(
        query="customer revenue by region",
        max_results=5,
    )
    for item in context:
        print(f"  [{item.get('score', 'N/A')}] {item.get('text', '')[:80]}...")

    # Vector similarity search: semantic RAG retrieval
    print("\n=== Vector Similarity Search ===")
    rag_context = agent.get_rag_context(
        query="which customers have the highest lifetime value",
        max_results=3,
    )
    for item in rag_context:
        print(f"  [{item.get('score', 'N/A')}] {item.get('text', '')[:80]}...")

    # Use context in a reasoning chain
    print("\n=== Reasoning Chain with Context ===")
    with agent.reasoning_chain("Analyze top customers") as chain:
        chain.step("Retrieve customer data context")
        context = agent.get_context(query="top customers", max_results=3)

        chain.step("Query for detailed analysis")
        rows = agent.query(
            "SELECT * FROM information_schema.tables LIMIT 3"
        )
        print(f"  Found {len(rows)} tables")

        chain.step("Synthesize findings")
        print("  Analysis complete")

    agent.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
