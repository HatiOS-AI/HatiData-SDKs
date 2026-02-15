# dbt-hatidata

[![PyPI version](https://img.shields.io/pypi/v/dbt-hatidata.svg)](https://pypi.org/project/dbt-hatidata/)
[![Python versions](https://img.shields.io/pypi/pyversions/dbt-hatidata.svg)](https://pypi.org/project/dbt-hatidata/)
[![License](https://img.shields.io/pypi/l/dbt-hatidata.svg)](https://github.com/HatiOS-AI/HatiData-Core/blob/main/LICENSE)

The [dbt](https://www.getdbt.com/) adapter for [HatiData](https://hatidata.com) In-VPC Data Warehouse.

HatiData is a Postgres wire-compatible, Snowflake SQL-compatible data warehouse that runs entirely inside your VPC. `dbt-hatidata` lets you use dbt to build, test, and document your data models on HatiData with full support for Snowflake SQL syntax -- no query rewrites required.

## Installation

```bash
pip install dbt-hatidata
```

Requires Python 3.9 or later and dbt-core 1.7+.

## Configuration

Add a HatiData target to your `~/.dbt/profiles.yml`:

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: hatidata
      host: "{{ env_var('HATIDATA_HOST', 'localhost') }}"
      port: 5439
      user: "{{ env_var('HATIDATA_USER', 'analyst') }}"
      password: "{{ env_var('HATIDATA_API_KEY') }}"
      database: iceberg_catalog
      schema: analytics
      environment: development
      api_key: "{{ env_var('HATIDATA_API_KEY') }}"
      auto_transpile: true
      threads: 4
      connect_timeout: 30
```

### Connection Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `type` | Must be `hatidata` | -- |
| `host` | HatiData proxy hostname or IP | `localhost` |
| `port` | HatiData proxy port | `5439` |
| `user` | Username for authentication | -- |
| `password` | API key used as password | -- |
| `database` | Catalog name | `iceberg_catalog` |
| `schema` | Default schema for models | `analytics` |
| `environment` | HatiData environment (`development`, `staging`, `production`) | `development` |
| `api_key` | HatiData API key for control plane authentication | -- |
| `auto_transpile` | Enable automatic Snowflake-to-DuckDB SQL transpilation | `true` |
| `threads` | Number of concurrent dbt threads | `4` |
| `connect_timeout` | Connection timeout in seconds | `30` |

## Features

### Snowflake SQL Compatibility

HatiData's built-in transpiler automatically converts Snowflake SQL to DuckDB-compatible SQL, so you can bring your existing Snowflake dbt models without changes:

- **Date/time functions**: `DATEADD`, `DATEDIFF`, `DATE_TRUNC`, `TO_DATE`, `TO_TIMESTAMP`
- **String aggregation**: `LISTAGG` with ordering and delimiter support
- **Semi-structured data**: `VARIANT` type mapped to JSON, `PARSE_JSON`, `GET_PATH`, colon notation (`col:field`)
- **Window functions**: `QUALIFY` clause for filtering window function results
- **Table functions**: `FLATTEN` for exploding arrays and objects
- **Type casting**: `::` cast syntax, Snowflake type aliases (`NUMBER`, `STRING`, `TIMESTAMP_NTZ`)

### Incremental Materializations

All standard dbt incremental strategies are supported:

- **`append`** -- Insert new rows without deduplication
- **`delete+insert`** -- Delete matching rows then insert (ideal for date-partitioned models)
- **`merge`** -- Upsert using a unique key (uses DuckDB's `INSERT ... ON CONFLICT`)

### Column Masking

HatiData's policy engine applies column-level masking rules automatically. Sensitive columns are masked at query time based on the authenticated user's role, and dbt models respect these policies transparently.

### Audit Logging

Every query executed by dbt is recorded in HatiData's immutable audit log, including the dbt model name, invocation ID, and execution metadata. Use the HatiData dashboard or `query_audit` table to inspect dbt run history.

## Supported dbt Commands

| Command | Status |
|---------|--------|
| `dbt run` | Supported |
| `dbt test` | Supported |
| `dbt seed` | Supported |
| `dbt snapshot` | Supported |
| `dbt docs generate` | Supported |
| `dbt docs serve` | Supported |
| `dbt build` | Supported |

## Migrating from Snowflake

If you are migrating an existing dbt project from Snowflake to HatiData, the process is straightforward:

1. Install `dbt-hatidata` alongside or in place of `dbt-snowflake`.
2. Update your `profiles.yml` to use `type: hatidata` with the connection parameters shown above.
3. Run `dbt run` -- HatiData's transpiler handles Snowflake SQL translation automatically.

Most Snowflake SQL constructs are supported out of the box. If the transpiler encounters an unsupported pattern, the AI healer attempts an automatic fix. Unsupported constructs are logged so you can address them incrementally.

For models that use Snowflake-specific macros (e.g., `dbt_utils.surrogate_key`), standard dbt packages continue to work since HatiData is Postgres wire-compatible.

## Development

```bash
# Clone the repository
git clone https://github.com/hatidata/dbt-hatidata.git
cd dbt-hatidata

# Install in development mode
pip install -e ".[dev]"

# Run unit tests
python -m pytest tests/unit/ -v

# Run functional tests (requires a running HatiData proxy on port 5439)
HATIDATA_HOST=localhost RUN_FUNCTIONAL=true bash ci/run_dbt_tests.sh
```

## Resources

- [HatiData Documentation](https://docs.hatiosai.com/hatidata)
- [dbt Documentation](https://docs.getdbt.com)
- [dbt Community Slack](https://community.getdbt.com)

## License

Apache License 2.0. Copyright (c) Marviy Pte Ltd. See [LICENSE](https://github.com/HatiOS-AI/HatiData-Core/blob/main/LICENSE) for details.
