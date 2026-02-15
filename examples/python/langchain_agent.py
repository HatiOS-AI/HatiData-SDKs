"""HatiData + LangChain — SQL Agent

Prerequisites:
    pip install hatidata-agent[langchain] langchain-openai

Usage:
    export OPENAI_API_KEY=sk-...
    python langchain_agent.py
"""

from hatidata_agent.langchain import HatiDataSQLDatabase
# Note: requires langchain and an LLM provider

def main():
    # HatiData exposes a Postgres-compatible wire protocol
    # LangChain's SQL agent works out of the box
    db = HatiDataSQLDatabase(
        host="localhost",
        port=5439,
        agent_id="langchain-sql-agent",
    )

    # List available tables
    print("Tables:", db.get_usable_table_names())

    # Get table info (schema + sample rows)
    print("\nTable info:")
    print(db.get_table_info())

    # Run a query directly
    result = db.run("SELECT COUNT(*) as total FROM information_schema.tables")
    print("\nQuery result:", result)

    # To use with a LangChain SQL agent:
    # from langchain_openai import ChatOpenAI
    # from langchain.agents import create_sql_agent
    # llm = ChatOpenAI(model="gpt-4o", temperature=0)
    # agent = create_sql_agent(llm=llm, db=db, verbose=True)
    # result = agent.run("How many tables are in the database?")

    print("\nDone! Uncomment the agent code above to use with an LLM.")


if __name__ == "__main__":
    main()
