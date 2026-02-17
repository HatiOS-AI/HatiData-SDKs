"""Shared test fixtures for dbt-hatidata tests."""

import os
import pytest
import psycopg2


HATIDATA_HOST = os.environ.get("HATIDATA_HOST", "localhost")
HATIDATA_PORT = int(os.environ.get("HATIDATA_PORT", "5439"))
HATIDATA_USER = os.environ.get("HATIDATA_USER", "admin")
HATIDATA_PASSWORD = os.environ.get("HATIDATA_PASSWORD", "")
HATIDATA_DATABASE = os.environ.get("HATIDATA_DATABASE", "iceberg_catalog")

if not HATIDATA_PASSWORD:
    pytest.skip(
        "HATIDATA_PASSWORD env var required for dbt integration tests",
        allow_module_level=True,
    )


@pytest.fixture(scope="session")
def hatidata_connection():
    """Create a connection to the HatiData proxy for testing."""
    try:
        conn = psycopg2.connect(
            host=HATIDATA_HOST,
            port=HATIDATA_PORT,
            user=HATIDATA_USER,
            password=HATIDATA_PASSWORD,
            dbname=HATIDATA_DATABASE,
            connect_timeout=10,
        )
        conn.autocommit = True
        yield conn
        conn.close()
    except psycopg2.OperationalError:
        pytest.skip("HatiData proxy not available")


@pytest.fixture
def cursor(hatidata_connection):
    """Get a cursor from the HatiData connection."""
    cur = hatidata_connection.cursor()
    yield cur
    cur.close()


@pytest.fixture(scope="session")
def dbt_project_dir(tmp_path_factory):
    """Create a temporary dbt project for testing."""
    project_dir = tmp_path_factory.mktemp("dbt_project")

    # Create dbt_project.yml
    (project_dir / "dbt_project.yml").write_text(
        """
name: test_project
version: "1.0.0"
config-version: 2
profile: test_hatidata

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
"""
    )

    # Create profiles.yml
    profiles_dir = project_dir / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "profiles.yml").write_text(
        f"""
test_hatidata:
  target: dev
  outputs:
    dev:
      type: hatidata
      host: {HATIDATA_HOST}
      port: {HATIDATA_PORT}
      user: {HATIDATA_USER}
      password: {HATIDATA_PASSWORD}
      database: {HATIDATA_DATABASE}
      schema: test_dbt
      environment: development
      auto_transpile: true
      threads: 1
      connect_timeout: 30
"""
    )

    # Create models directory
    (project_dir / "models").mkdir()
    (project_dir / "seeds").mkdir()
    (project_dir / "tests").mkdir()

    return project_dir
