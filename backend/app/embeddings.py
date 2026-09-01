"""Turns text into a fixed-length vector for pgvector similarity search.

Two providers, same interface (embed_query / embed_passages):

- VoyageEmbeddingProvider: real Voyage AI API. Used when GRIDOPS_VOYAGE_API_KEY
  is set. Voyage's API distinguishes "document" vs "query" embeddings
  (input_type) so a question and the passage it should match aren't encoded
  identically -- this measurably improves retrieval.
- DeterministicEmbeddingProvider: a hash of the text, no network call. Lets
  the whole RAG pipeline run with zero configuration. This is NOT semantic
  search -- it is a stand-in so the demo works out of the box.
"""

from __future__ import annotations

import hashlib
import json
import math
from urllib.request import Request, urlopen

from .config import settings

DIMENSIONS = 256


class DeterministicEmbeddingProvider:
    dimensions = DIMENSIONS

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.blake2b(text.encode("utf-8"), digest_size=64).digest()
        values: list[float] = []
        while len(values) < self.dimensions:
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) >= self.dimensions:
                    break
            digest = hashlib.blake2b(digest, digest_size=64).digest()
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]


class VoyageEmbeddingProvider:
    dimensions = None  # set after the first real response

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], input_type="query")[0]

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, input_type="document")

    def _embed(self, texts: list[str], *, input_type: str) -> list[list[float]]:
        body = json.dumps({"input": texts, "model": self._model, "input_type": input_type}).encode()
        request = Request(
            "https://api.voyageai.com/v1/embeddings",
            data=body,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
        ordered = sorted(payload["data"], key=lambda item: item["index"])
        vectors = [item["embedding"] for item in ordered]
        self.dimensions = len(vectors[0])
        return vectors


def get_embedding_provider():
    if settings.voyage_api_key:
        return VoyageEmbeddingProvider(settings.voyage_api_key, settings.voyage_model)
    return DeterministicEmbeddingProvider()
