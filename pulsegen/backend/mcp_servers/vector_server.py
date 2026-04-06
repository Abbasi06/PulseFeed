from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import chromadb
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

TOOLS_MANIFEST: list[dict[str, Any]] = [
    {
        "name": "upsert",
        "description": "Insert or update a document in the vector store.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "text": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["id", "text", "metadata"],
        },
    },
    {
        "name": "search",
        "description": "Semantic search over the vector store.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query_text": {"type": "string"},
                "filters": {"type": ["object", "null"]},
                "top_k": {"type": "integer", "default": 10},
            },
            "required": ["query_text"],
        },
    },
]


def _build_clients() -> tuple[chromadb.Collection, genai.Client]:
    chroma_client = chromadb.PersistentClient(
        path=os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
    )
    collection_name = os.environ.get("CHROMA_COLLECTION", "generator_docs")
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    genai_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return collection, genai_client


_collection: chromadb.Collection
_genai_client: genai.Client
_collection, _genai_client = _build_clients()


def _embed(text: str, task_type: str) -> list[float]:
    response = _genai_client.models.embed_content(
        model="models/text-embedding-004",
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    embeddings = response.embeddings or []
    return list(embeddings[0].values or [])


def _tool_upsert(arguments: dict[str, Any]) -> dict[str, Any]:
    doc_id: str = arguments["id"]
    text: str = arguments["text"]
    metadata: dict[str, Any] = arguments["metadata"]

    existing = _collection.get(ids=[doc_id])
    status = "updated" if existing["ids"] else "created"

    vector = _embed(text, "RETRIEVAL_DOCUMENT")
    _collection.upsert(
        ids=[doc_id],
        embeddings=[vector],
        documents=[text],
        metadatas=[metadata],
    )
    return {"id": doc_id, "status": status}


def _tool_search(arguments: dict[str, Any]) -> dict[str, Any]:
    query_text: str = arguments["query_text"]
    filters: dict[str, Any] | None = arguments.get("filters")
    top_k: int = int(arguments.get("top_k", 10))

    vector = _embed(query_text, "RETRIEVAL_QUERY")
    query_kwargs: dict[str, Any] = {
        "query_embeddings": [vector],
        "n_results": top_k,
    }
    if filters:
        query_kwargs["where"] = filters

    raw = _collection.query(**query_kwargs)
    ids: list[str] = raw["ids"][0] if raw["ids"] else []
    distances: list[float] = raw["distances"][0] if raw["distances"] else []
    metadatas: list[dict[str, Any]] = raw["metadatas"][0] if raw["metadatas"] else []  # type: ignore[assignment,unused-ignore]

    results = [
        {"id": ids[i], "distance": distances[i], "metadata": metadatas[i]}
        for i in range(len(ids))
    ]
    return {"results": results}


def _handle_tools_list(request_id: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS_MANIFEST}}


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    name: str = params.get("name", "")
    arguments: dict[str, Any] = params.get("arguments", {})

    if name == "upsert":
        result = _tool_upsert(arguments)
    elif name == "search":
        result = _tool_search(arguments)
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown tool: {name}"},
        }

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("id")
    method: str = request.get("method", "")
    params: dict[str, Any] = request.get("params", {})

    if method == "tools/list":
        return _handle_tools_list(request_id)
    if method == "tools/call":
        return _handle_tools_call(request_id, params)

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logger.info("vector server started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
