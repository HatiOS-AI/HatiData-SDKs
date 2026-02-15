"""Unit tests for HatiData connection manager."""

import pytest
from unittest.mock import MagicMock, patch
from dbt.adapters.hatidata.connections import (
    HatiDataCredentials,
    HatiDataConnectionManager,
)


class TestHatiDataCredentials:
    """Test credential configuration."""

    def test_type_returns_hatidata(self):
        creds = HatiDataCredentials(
            host="localhost",
            port=5439,
            user="admin",
            password="test",
            database="iceberg_catalog",
            schema="public",
        )
        assert creds.type == "hatidata"

    def test_unique_field_is_host(self):
        creds = HatiDataCredentials(
            host="proxy.example.com",
            port=5439,
            user="admin",
            password="test",
            database="iceberg_catalog",
            schema="public",
        )
        assert creds.unique_field == "proxy.example.com"

    def test_connection_keys(self):
        creds = HatiDataCredentials(
            host="localhost",
            port=5439,
            user="admin",
            password="test",
            database="iceberg_catalog",
            schema="public",
        )
        keys = creds._connection_keys()
        assert "host" in keys
        assert "port" in keys
        assert "environment" in keys
        assert "auto_transpile" in keys

    def test_default_environment(self):
        creds = HatiDataCredentials(
            host="localhost",
            port=5439,
            user="admin",
            password="test",
            database="iceberg_catalog",
            schema="public",
        )
        assert creds.environment == "production"

    def test_custom_environment(self):
        creds = HatiDataCredentials(
            host="localhost",
            port=5439,
            user="admin",
            password="test",
            database="iceberg_catalog",
            schema="public",
            environment="development",
        )
        assert creds.environment == "development"

    def test_default_auto_transpile(self):
        creds = HatiDataCredentials(
            host="localhost",
            port=5439,
            user="admin",
            password="test",
            database="iceberg_catalog",
            schema="public",
        )
        assert creds.auto_transpile is True


class TestHatiDataConnectionManager:
    """Test connection manager."""

    def test_type_is_hatidata(self):
        assert HatiDataConnectionManager.TYPE == "hatidata"

    def test_get_response(self):
        cursor = MagicMock()
        cursor.rowcount = 42
        cursor.statusmessage = "SELECT 42"

        response = HatiDataConnectionManager.get_response(cursor)
        assert response.rows_affected == 42
        assert "42" in response._message

    def test_get_response_zero_rows(self):
        cursor = MagicMock()
        cursor.rowcount = 0
        cursor.statusmessage = "SELECT 0"

        response = HatiDataConnectionManager.get_response(cursor)
        assert response.rows_affected == 0

    def test_get_response_no_status(self):
        cursor = MagicMock()
        cursor.rowcount = 1
        cursor.statusmessage = None

        response = HatiDataConnectionManager.get_response(cursor)
        assert response.rows_affected == 1
        assert response.code == ""
