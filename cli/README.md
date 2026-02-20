# hati -- HatiData CLI

Local-first data warehouse for AI agents. Write Snowflake-compatible SQL, run it on DuckDB.

## Install

```bash
# Cargo (macOS/Linux/Windows)
cargo install hatidata-cli

# Binary download
# See Releases: https://github.com/HatiOS-AI/HatiData-Core/releases
```

## Quick Start

```bash
# Initialize a local warehouse (interactive signup wizard included)
hati init my-project
cd my-project

# Run queries with Snowflake-compatible SQL
hati query "CREATE TABLE events (id INT, name VARCHAR, ts TIMESTAMP_NTZ)"
hati query "INSERT INTO events VALUES (1, 'signup', CURRENT_TIMESTAMP)"
hati query "SELECT DATEDIFF('day', ts, CURRENT_TIMESTAMP) as days_ago FROM events"

# Check status
hati status

# Sign up for a free account (required for push/pull)
hati auth signup

# Push to cloud when ready
hati push --target cloud
```

## Commands

### Core

| Command | Description |
|---------|-------------|
| `hati init [path]` | Initialize a new local warehouse (with interactive signup) |
| `hati query <sql>` | Execute SQL against local DuckDB |
| `hati query -f <file.sql>` | Execute SQL from a file |
| `hati status` | Show warehouse info, tables, config |

### Cloud Sync (requires authentication)

| Command | Description |
|---------|-------------|
| `hati push --target <cloud\|vpc>` | Push local tables to cloud or VPC |
| `hati push --target cloud --tier cloud` | Push with explicit tier override |
| `hati push -T table1,table2` | Push specific tables only |
| `hati pull` | Pull schema/data from remote (Cloud tier+) |
| `hati pull -T table1` | Pull specific tables |

### Authentication

| Command | Description |
|---------|-------------|
| `hati auth signup` | Create a new HatiData account |
| `hati auth login` | Log in with email and password |
| `hati auth status` | Show current auth status (tier, org, masked key) |
| `hati auth logout` | Clear local session |
| `hati auth upgrade` | Open billing page in browser |

### Configuration

| Command | Description |
|---------|-------------|
| `hati config set <key> <value>` | Set configuration |
| `hati config get <key>` | Get configuration value |
| `hati config list` | List all configuration |
| `hati dashboard [page]` | Open HatiData dashboard in browser |

## Authentication

Cloud features (push, pull) require a free HatiData account. The CLI enforces authentication before any cloud operation.

```bash
# Option 1: Sign up from the CLI
hati auth signup

# Option 2: Log in with existing credentials
hati auth login

# Option 3: Set API key directly
hati config set api_key hd_live_your_key_here

# Verify your auth status
hati auth status
```

During `hati init`, an interactive wizard offers three choices:
1. **Sign up free** — create account, get API key
2. **Enter existing API key** — validate and save
3. **Local-only** — skip auth, use local DuckDB only

Session tokens are stored in `.hati/session.json` (gitignored). API keys are stored in `.hati/config.toml`.

## Tier Enforcement

The CLI enforces per-tier limits before pushing data. All cloud operations require authentication.

| | Free | Cloud | Growth | Enterprise |
|---|---|---|---|---|
| **Tables per push** | 5 | 50 | 500 | Unlimited |
| **Rows per table** | 10,000 | 1,000,000 | 100,000,000 | Unlimited |
| **Push size per table** | 10 MB | 100 MB | 1 GB | Unlimited |
| **Pull data** | -- | Yes | Yes | Yes |
| **VPC push** | -- | -- | Yes | Yes |

Tables or files that exceed tier limits are skipped with a clear error message and upgrade hint. The `--tier` flag lets you override the tier for a single operation (server-side limits still apply).

```bash
# Push with default tier (from config or Free)
hati push --target cloud

# Override tier for this push
hati push --target cloud --tier cloud

# VPC push requires Growth or Enterprise
hati push --target vpc --tier growth
```

## Configuration

Configuration is stored in `.hati/config.toml` (project-level).

| Key | Description | Default |
|-----|-------------|---------|
| `cloud_endpoint` | HatiData cloud API endpoint | `https://api.hatidata.com` |
| `api_key` | API key for authentication (`hd_live_...`) | -- |
| `tier` | Account tier (free, cloud, growth, enterprise) | `free` |
| `org_id` | Organization ID | -- |
| `default_target` | Default push target: `cloud` or `vpc` | -- |

## Dashboard Deep Links

Open specific dashboard pages directly from the CLI:

```bash
hati dashboard billing       # Billing and subscription
hati dashboard onboarding    # Setup wizard
hati dashboard agents        # Agent overview
hati dashboard api-keys      # API key management
hati dashboard triggers      # Semantic triggers
hati dashboard branches      # State branches
hati dashboard cot           # Chain-of-thought replay
hati dashboard policies      # Access policies
```

## Project Structure

```
my-project/
  .hati/
    config.toml       # Cloud endpoint, API key, tier, org_id
    session.json      # JWT session token (gitignored)
    local.duckdb      # Local DuckDB database (gitignored)
  .gitignore          # Auto-generated: excludes .duckdb, session.json
```

## Links

- Docs: https://docs.hatidata.com
- Repository: https://github.com/HatiOS-AI/HatiData-Core
- Website: https://hatidata.com
- Pricing: https://hatidata.com/pricing

## License

Apache-2.0
