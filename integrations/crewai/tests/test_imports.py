"""Smoke tests to verify crewai-hatidata can be imported.

Note: These tests require crewai to be installed. They are skipped
if crewai is not available.
"""

import importlib


def test_import_memory():
    """Test that HatiDataMemory can be imported."""
    # Memory module only depends on hatidata_agent, not crewai
    from crewai_hatidata.memory import HatiDataMemory
    assert HatiDataMemory is not None


def test_import_tools():
    """Test that tools module can be imported (requires crewai)."""
    try:
        importlib.import_module("crewai")
    except ImportError:
        import pytest
        pytest.skip("crewai not installed")

    from crewai_hatidata.tools import (
        HatiDataQueryTool,
        HatiDataListTablesTool,
        HatiDataDescribeTableTool,
        HatiDataContextSearchTool,
    )
    assert HatiDataQueryTool is not None
    assert HatiDataListTablesTool is not None
    assert HatiDataDescribeTableTool is not None
    assert HatiDataContextSearchTool is not None
