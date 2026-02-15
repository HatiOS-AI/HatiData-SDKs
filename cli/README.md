# hati -- HatiData CLI

Local-first data warehouse for AI agents. Write Snowflake-compatible SQL, run it on DuckDB.

## Install

```bash
# Homebrew (macOS/Linux)
brew install hatidata/tap/hati

# Cargo
cargo install hati

# Binary download
# See Releases: https://github.com/HatiOS-AI/hatidata-core/releases
```

## Quick Start

```bash
# Initialize a local warehouse
hati init my-project
cd my-project

# Run queries with Snowflake-compatible SQL
hati query "CREATE TABLE events (id INT, name VARCHAR, ts TIMESTAMP_NTZ)"
hati query "INSERT INTO events VALUES (1, 'signup', CURRENT_TIMESTAMP)"
hati query "SELECT DATEDIFF('day', ts, CURRENT_TIMESTAMP) as days_ago FROM events"

# Check status
hati status

# Push to cloud when ready
hati push --target cloud
```

## Commands

| Command | Description |
|---------|-------------|
| `hati init [path]` | Initialize a new local warehouse |
| `hati query <sql>` | Execute SQL against local DuckDB |
| `hati query -f <file.sql>` | Execute SQL from a file |
| `hati status` | Show warehouse info, tables, config |
| `hati push --target <cloud\|vpc>` | Push local data to cloud or VPC |
| `hati pull` | Pull schema/data from remote |
| `hati config set <key> <value>` | Set configuration |
| `hati config get <key>` | Get configuration value |
| `hati config list` | List all configuration |

## Configuration

Configuration is stored in `.hati/config.toml` (project-level).

| Key | Description |
|-----|-------------|
| `cloud_endpoint` | HatiData cloud API endpoint |
| `api_key` | API key for authentication (`hd_live_...`) |
| `default_target` | Default push target: `cloud` or `vpc` |
| `org_id` | Organization ID |

## Three-Tier Model

**Local (Free)** -- DuckDB on your machine, zero cloud dependency. Initialize with `hati init`, query with `hati query`. All data stays local in `.hati/local.duckdb`.

**Cloud ($29/mo)** -- Push local data to a managed HatiData warehouse with `hati push --target cloud`. Get a Snowflake-compatible endpoint for your team and AI agents.

**Enterprise** -- Push to your own VPC with `hati push --target vpc`. Data never leaves your infrastructure, connected via AWS PrivateLink.

## Links

- Docs: https://docs.hatiosai.com/hatidata
- Repository: https://github.com/HatiOS-AI/hatidata-core
- Website: https://hatidata.com

## License

Apache-2.0
