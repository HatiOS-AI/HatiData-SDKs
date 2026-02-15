"""HatiData + CrewAI — Data Analyst Agent

Prerequisites:
    pip install crewai-hatidata crewai

Usage:
    python crewai_agent.py
"""

# Note: This is a structural example showing how to wire up CrewAI with HatiData.
# Running it requires a configured LLM (e.g., OPENAI_API_KEY set).

def main():
    print("CrewAI + HatiData Integration Example")
    print("=" * 40)

    # Import HatiData tools for CrewAI
    from crewai_hatidata import (
        HatiDataQueryTool,
        HatiDataListTablesTool,
        HatiDataDescribeTableTool,
    )

    # Create tools pointing to your HatiData instance
    query_tool = HatiDataQueryTool(host="localhost", port=5439)
    list_tables_tool = HatiDataListTablesTool(host="localhost", port=5439)
    describe_tool = HatiDataDescribeTableTool(host="localhost", port=5439)

    print(f"Tools created: {query_tool.name}, {list_tables_tool.name}, {describe_tool.name}")

    # To use with a CrewAI agent:
    # from crewai import Agent, Task, Crew
    #
    # analyst = Agent(
    #     role="Data Analyst",
    #     goal="Analyze data in the HatiData warehouse",
    #     backstory="You are a data analyst with SQL expertise.",
    #     tools=[query_tool, list_tables_tool, describe_tool],
    # )
    #
    # task = Task(
    #     description="List all tables and describe their schemas.",
    #     agent=analyst,
    # )
    #
    # crew = Crew(agents=[analyst], tasks=[task])
    # result = crew.kickoff()
    # print(result)

    print("\nUncomment the agent code above to run with an LLM.")


if __name__ == "__main__":
    main()
