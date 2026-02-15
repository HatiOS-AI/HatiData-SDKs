# Contributing to HatiData

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Prerequisites

- **Rust 1.75+** (for the CLI)
- **Python 3.9+** (for the Python SDK and integrations)
- **Node.js 18+** (for the TypeScript SDK)

## Development Setup

### CLI (`cli/`)

```bash
cd cli
cargo build
cargo test
cargo clippy
```

### Python SDK (`sdk/python/`)

```bash
cd sdk/python
pip install -e ".[dev]"
python -c "from hatidata_agent import HatiDataAgent; print('OK')"
```

### TypeScript SDK (`sdk/typescript/`)

```bash
cd sdk/typescript
npm install
npm run build
npm test
```

### Integrations

```bash
# LangChain
cd integrations/langchain && pip install -e .

# CrewAI
cd integrations/crewai && pip install -e .

# dbt adapter
cd integrations/dbt && pip install -e ".[dev]" && pytest
```

## Code Style

- **Rust**: `cargo fmt` + `cargo clippy -- -D warnings`
- **TypeScript**: ESLint (`npm run lint`)
- **Python**: Follow existing patterns in each package

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(cli): add hati export command
fix(python-sdk): handle connection timeout
docs: update quickstart example
chore(ci): add Python 3.13 to test matrix
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes and add tests
4. Run the relevant test suite (see Development Setup above)
5. Commit with a conventional commit message
6. Open a pull request against `main`

## What to Contribute

- **SQL function mappings** — Add new Snowflake-to-DuckDB function transpilations
- **Framework integrations** — Add support for new AI agent frameworks
- **Examples** — Real-world usage examples in `examples/`
- **Documentation** — Improve READMEs, add code comments
- **Bug fixes** — Fix issues in the CLI, SDKs, or integrations
- **Tests** — Increase coverage across all packages

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please read it before participating.

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.
