"""RAG layer: embeds tips.txt into a local Chroma collection and retrieves
the most relevant tips for a destination."""

import os

import chromadb
from openai import OpenAI

TIPS_FILE = "tips.txt"
CHROMA_DIR = "./chroma"
COLLECTION_NAME = "travel_tips"
EMBEDDING_MODEL = "text-embedding-3-small"

_client = None
_collection = None


def _get_openai_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _embed(texts):
    client = _get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def get_collection():
    """Return the Chroma collection, building it from tips.txt on first call."""
    global _client, _collection

    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = _client.get_or_create_collection(COLLECTION_NAME)

    if _collection.count() == 0:
        with open(TIPS_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if lines:
            embeddings = _embed(lines)
            ids = [f"tip-{i}" for i in range(len(lines))]
            _collection.add(ids=ids, embeddings=embeddings, documents=lines)

    return _collection


def retrieve_tips(destination: str, n_results: int = 3):
    """Return the n_results tips most relevant to the destination."""
    collection = get_collection()
    if collection.count() == 0:
        return []

    query_embedding = _embed([destination])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
    )
    return results["documents"][0] if results["documents"] else []
