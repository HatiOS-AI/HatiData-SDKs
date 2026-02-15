"""HatiData Python SDK — Quickstart

Prerequisites:
    pip install hatidata-agent

Usage:
    # Start HatiData locally first:
    hati init my-warehouse

    # Then run this script:
    python quickstart.py
"""

from hatidata_agent import HatiDataAgent


def main():
    # Connect to local HatiData instance
    agent = HatiDataAgent(
        host="localhost",
        port=5439,
        agent_id="quickstart-example",
        agent_framework="custom",
    )

    # Create a table using Snowflake-compatible SQL
    agent.execute(
        "CREATE TABLE IF NOT EXISTS events (id INT, name VARCHAR, created_at TIMESTAMP_NTZ)"
    )

    # Insert data
    agent.execute(
        "INSERT INTO events VALUES (1, 'signup', CURRENT_TIMESTAMP)"
    )

    # Query with Snowflake functions — they get transpiled automatically
    rows = agent.query("SELECT id, name, NVL(name, 'unknown') as safe_name FROM events")
    for row in rows:
        print(row)

    # Check what tables exist
    tables = agent.query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")
    print("\nTables:", [t[0] for t in tables])

    agent.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
