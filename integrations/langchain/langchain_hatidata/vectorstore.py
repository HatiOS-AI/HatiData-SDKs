"""LangChain VectorStore backed by HatiData.

Uses HatiData's built-in vector similarity search (backed by Qdrant)
for retrieval-augmented generation (RAG) workflows.

Usage::

    from langchain_hatidata import HatiDataVectorStore
    from langchain_openai import OpenAIEmbeddings

    vectorstore = HatiDataVectorStore(
        host="proxy.internal",
        agent_id="rag-agent",
        table="documents",
        embedding_column="embedding",
        content_column="content",
        embedding=OpenAIEmbeddings(),
    )

    docs = vectorstore.similarity_search("enterprise pricing", k=5)
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Iterable, Optional, Type

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore

from hatidata_agent import HatiDataAgent


class HatiDataVectorStore(VectorStore):
    """LangChain VectorStore backed by HatiData's vector search.

    Stores document embeddings in a HatiData table and performs
    similarity search via ``hatidata_rag_context()`` UDF.

    The embeddings table is auto-created if it doesn't exist::

        CREATE TABLE IF NOT EXISTS {table} (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            metadata TEXT,
            {embedding_column} FLOAT[{dimension}]
        )
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5439,
        agent_id: str = "langchain-agent",
        table: str = "langchain_documents",
        embedding_column: str = "embedding",
        content_column: str = "content",
        metadata_column: str = "metadata",
        embedding: Optional[Embeddings] = None,
        database: str = "hatidata",
        user: str = "agent",
        password: str = "",
    ):
        self._agent = HatiDataAgent(
            host=host,
            port=port,
            agent_id=agent_id,
            framework="langchain",
            database=database,
            user=user,
            password=password,
        )
        self._table = table
        self._embedding_column = embedding_column
        self._content_column = content_column
        self._metadata_column = metadata_column
        self._embedding = embedding
        self._table_created = False

    @property
    def embeddings(self) -> Optional[Embeddings]:
        return self._embedding

    def _ensure_table(self, dimension: int) -> None:
        """Create the embeddings table if it doesn't exist."""
        if self._table_created:
            return
        self._agent.execute(
            f"CREATE TABLE IF NOT EXISTS {self._table} ("
            f"  id TEXT PRIMARY KEY,"
            f"  {self._content_column} TEXT NOT NULL,"
            f"  {self._metadata_column} TEXT,"
            f"  {self._embedding_column} FLOAT[{dimension}]"
            f")"
        )
        self._table_created = True

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[list[dict]] = None,
        **kwargs: Any,
    ) -> list[str]:
        """Add texts with embeddings to HatiData.

        Args:
            texts: Texts to add.
            metadatas: Optional metadata for each text.

        Returns:
            List of IDs for the added documents.
        """
        if self._embedding is None:
            raise ValueError("Embeddings model required. Pass embedding= to constructor.")

        text_list = list(texts)
        vectors = self._embedding.embed_documents(text_list)

        if vectors:
            self._ensure_table(len(vectors[0]))

        ids = []
        for i, (text, vector) in enumerate(zip(text_list, vectors)):
            doc_id = uuid.uuid4().hex
            ids.append(doc_id)
            meta = json.dumps(metadatas[i]) if metadatas and i < len(metadatas) else "{}"
            vec_str = f"[{', '.join(str(v) for v in vector)}]"
            self._agent.execute(
                f"INSERT INTO {self._table} "
                f"(id, {self._content_column}, {self._metadata_column}, {self._embedding_column}) "
                f"VALUES ('{doc_id}', '{_escape(text)}', '{_escape(meta)}', {vec_str})"
            )
        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        **kwargs: Any,
    ) -> list[Document]:
        """Search for similar documents.

        Args:
            query: Search query text.
            k: Number of results to return.

        Returns:
            List of matching LangChain Documents.
        """
        if self._embedding is None:
            raise ValueError("Embeddings model required for similarity search.")

        query_vector = self._embedding.embed_query(query)
        return self.similarity_search_by_vector(query_vector, k=k, **kwargs)

    def similarity_search_by_vector(
        self,
        embedding: list[float],
        k: int = 4,
        **kwargs: Any,
    ) -> list[Document]:
        """Search by embedding vector.

        Args:
            embedding: Query embedding vector.
            k: Number of results to return.

        Returns:
            List of matching LangChain Documents.
        """
        rows = self._agent.get_rag_context(
            table=self._table,
            embedding_col=self._embedding_column,
            vector=embedding,
            top_k=k,
        )

        docs = []
        for row in rows:
            content = row.get(self._content_column, "")
            meta_str = row.get(self._metadata_column, "{}")
            try:
                metadata = json.loads(meta_str) if meta_str else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            docs.append(Document(page_content=content, metadata=metadata))
        return docs

    @classmethod
    def from_texts(
        cls: Type[HatiDataVectorStore],
        texts: list[str],
        embedding: Embeddings,
        metadatas: Optional[list[dict]] = None,
        **kwargs: Any,
    ) -> HatiDataVectorStore:
        """Create a HatiDataVectorStore from a list of texts.

        Args:
            texts: Texts to add.
            embedding: Embeddings model.
            metadatas: Optional metadata for each text.
            **kwargs: Passed to constructor (host, port, agent_id, table, etc.)

        Returns:
            HatiDataVectorStore instance with documents added.
        """
        store = cls(embedding=embedding, **kwargs)
        store.add_texts(texts, metadatas=metadatas)
        return store


def _escape(s: str) -> str:
    """Escape single quotes for SQL insertion."""
    return s.replace("'", "''")
