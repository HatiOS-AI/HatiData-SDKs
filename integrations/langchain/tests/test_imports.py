"""Smoke tests to verify langchain-hatidata can be imported."""


def test_import_memory():
    from langchain_hatidata.memory import HatiDataMemory
    assert HatiDataMemory is not None


def test_import_vectorstore():
    from langchain_hatidata.vectorstore import HatiDataVectorStore
    assert HatiDataVectorStore is not None


def test_import_tools():
    from langchain_hatidata.tools import HatiDataToolkit
    assert HatiDataToolkit is not None


def test_top_level_import():
    from langchain_hatidata import HatiDataMemory, HatiDataVectorStore, HatiDataToolkit
    assert HatiDataMemory is not None
    assert HatiDataVectorStore is not None
    assert HatiDataToolkit is not None
