# HatiData Examples

Runnable examples for every HatiData package.

| Example | Language | Description | Prerequisites |
|---------|----------|-------------|---------------|
| `python/quickstart.py` | Python | Connect and query | `pip install hatidata-agent` |
| `python/langchain_agent.py` | Python | LangChain SQL agent | `pip install -r requirements.txt` |
| `python/crewai_agent.py` | Python | CrewAI with HatiData tools | `pip install -r requirements.txt` |
| `python/mcp_server.py` | Python | Start MCP server | `pip install hatidata-agent[mcp]` |
| `python/rag_search.py` | Python | RAG context retrieval | `pip install hatidata-agent` |
| `typescript/quickstart.ts` | TypeScript | Connect and query | `npm install` |
| `typescript/local_mode.ts` | TypeScript | DuckDB-WASM local engine | `npm install` |
| `dbt/sample_project/` | SQL/YAML | Minimal dbt project | `pip install dbt-hatidata` |
| `sql/*.sql` | SQL | Snowflake SQL samples | `hati` CLI |

## Running the examples

### Python

```bash
cd python
pip install -r requirements.txt
python quickstart.py
```

### TypeScript

```bash
cd typescript
npm install
npx tsx quickstart.ts
```

### dbt

```bash
cd dbt/sample_project
pip install dbt-hatidata
dbt seed
dbt run
```

### SQL

```bash
# Start HatiData locally, then run any SQL file:
hati init my-warehouse
psql -h localhost -p 5439 -U admin -f sql/001_basic_select.sql
```
