"""HatiData connection manager — extends Postgres wire protocol."""

from dataclasses import dataclass
from typing import Optional

from dbt.adapters.postgres.connections import PostgresConnectionManager, PostgresCredentials
from dbt.adapters.contracts.connection import AdapterResponse
import psycopg2


@dataclass
class HatiDataCredentials(PostgresCredentials):
    """HatiData connection credentials — extends Postgres."""

    environment: str = "production"
    api_key: str = ""
    auto_transpile: bool = True

    @property
    def type(self):
        return "hatidata"

    @property
    def unique_field(self):
        return self.host

    def _connection_keys(self):
        return (
            "host",
            "port",
            "user",
            "database",
            "schema",
            "environment",
            "auto_transpile",
        )


class HatiDataConnectionManager(PostgresConnectionManager):
    """Manages connections to HatiData via Postgres wire protocol."""

    TYPE = "hatidata"

    @classmethod
    def open(cls, connection):
        """Open connection to HatiData proxy via Postgres wire protocol."""
        credentials = connection.credentials

        kwargs = {
            "host": credentials.host,
            "port": credentials.port,
            "user": credentials.user,
            "password": credentials.password,
            "dbname": credentials.database,
            "connect_timeout": credentials.connect_timeout,
            "application_name": f"dbt-hatidata/{credentials.environment}",
        }

        # Add SSL if not connecting to localhost
        if credentials.host not in ("localhost", "127.0.0.1"):
            kwargs["sslmode"] = "require"

        # Pass HatiData-specific options via connection string options
        options_parts = []
        if credentials.environment:
            options_parts.append(f"-c hatidata.environment={credentials.environment}")
        if credentials.api_key:
            options_parts.append(f"-c hatidata.api_key={credentials.api_key}")
        if credentials.auto_transpile is not None:
            options_parts.append(
                f"-c hatidata.transpile={'true' if credentials.auto_transpile else 'false'}"
            )
        if options_parts:
            kwargs["options"] = " ".join(options_parts)

        handle = psycopg2.connect(**kwargs)
        handle.autocommit = True
        connection.handle = handle
        connection.state = "open"
        return connection

    def cancel(self, connection):
        """Cancel a running query."""
        try:
            connection.handle.cancel()
        except Exception:
            pass

    @classmethod
    def get_response(cls, cursor) -> AdapterResponse:
        """Parse query response from HatiData proxy."""
        rows = cursor.rowcount
        status = cursor.statusmessage or ""
        return AdapterResponse(
            _message=f"OK {rows}",
            rows_affected=rows,
            code=status,
        )
