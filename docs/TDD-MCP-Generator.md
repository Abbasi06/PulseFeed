# Technical Design Document: MCP-Driven Generator (Ingestion Engine)
## PulseBoard — Inference Cascade v1.0

**Status:** Draft
**Author:** Backend Architect
**Date:** 2026-03-25
**Scope:** Asynchronous document ingestion pipeline executing a four-phase Inference Cascade via a Generator Agent that calls MCP-compliant tool servers exclusively. No changes to `agents/research_agent.py`.

---

## Table of Contents

1. MCP Architecture Overview
2. MCP Server Configurations
3. Celery Worker Structure
4. Pydantic Schemas
5. Taxonomy Design
6. Generator Agent Architecture
7. Integration with Existing Code
8. File and Module Layout
9. Dependency Manifest
10. Risk and Trade-off Analysis

---

## 1. MCP Architecture Overview

### What is MCP

Model Context Protocol (MCP) is a JSON-RPC 2.0-based open standard that defines how AI agents discover and invoke tools provided by external servers. An MCP server is a long-running process that advertises a manifest of callable tools, accepts tool invocation requests from an agent, executes the work using whatever underlying library or API it wraps, and returns a structured response. The agent itself has no knowledge of how a tool is implemented — it only knows the tool's name, input schema, and output schema as declared in the manifest.

In this architecture the Generator Agent is a Gemini-powered tool-calling agent. Its only mechanism for touching external systems is to emit a `tools/call` JSON-RPC request to one of three MCP servers. Those servers are the sole holders of import statements for `arxiv`, `feedparser`, `sqlite3`, and `chromadb`. The agent code contains none of those imports.

### MCP Tool-Call Flow

```
Celery Worker
    |
    | dispatches task
    v
Generator Agent (gemini function-calling loop)
    |
    | emits JSON-RPC 2.0:  {"method": "tools/call", "params": {"name": "search", ...}}
    v
MCP Server Process (stdio transport)
    |
    | executes underlying library call
    v
External System (ArXiv API / SQLite file / ChromaDB in-process)
    |
    | returns raw result
    v
MCP Server (serializes to MCPToolResult JSON)
    |
    | writes to stdout (stdio transport)
    v
Generator Agent receives structured result, continues loop
```

The agent communicates with each MCP server over **stdio**. The Celery worker launches each server as a subprocess and holds open its stdin/stdout pipes for the duration of the task. There is no HTTP hop inside the worker process. This keeps latency minimal and eliminates the need for port assignment or service discovery during local execution.

### Contrast with `research_agent.py`

`research_agent.py` is a **direct-call agent**: it imports `ddgs.DDGS`, `google.genai`, and `sqlalchemy.orm.Session`, calls them as Python functions, and manually serializes results into dicts. Every external system it touches is hardcoded as a Python import. This is fast to write and easy to debug but has three structural limitations:

- Swapping the search backend (e.g., from DuckDuckGo to ArXiv) requires editing the agent file.
- There is no tool call audit log — it is impossible to replay what the agent did without re-running the whole pipeline.
- Testing requires mocking Python imports rather than substituting a mock MCP server.

The MCP-driven Generator Agent inverts this. The agent file describes *what* to do; the MCP servers describe *how*. Swapping ArXiv for a different API means updating `mcp_servers/search_server.py`, not touching any agent logic.

---

## 2. MCP Server Configurations

### 2.1 `mcp-search-tool`

**Purpose:** Unified search interface over ArXiv, GitHub, and RSS feeds.

**Transport:** stdio

**Underlying libraries:** `arxiv` Python SDK, `httpx` (GitHub REST API), `feedparser`

**Tool registered:**

```
name:   search
input:  {
          "query":       string,   // free-text search query
          "source":      enum["arxiv", "github", "rss"],
          "max_results": integer   // 1–50, default 10
        }
output: {
          "items": [
            {
              "title":        string,
              "url":          string,
              "body":         string,  // abstract, README excerpt, or feed entry body
              "author":       string,
              "published_at": string,  // ISO 8601
              "source":       string   // mirrors input source
            }
          ]
        }
```

**Launch configuration:**

```
command: uv run python -m backend.mcp_servers.search_server
args:    []
env:
  GITHUB_TOKEN: <from Vault / environment>
```

The server reads from stdin and writes to stdout in a line-delimited JSON-RPC loop. It does not require the GEMINI_API_KEY.

**Per-source behavior:**
- `arxiv`: Uses the `arxiv` SDK `Search` class with `max_results`. Maps `entry.summary` to `body`.
- `github`: Calls `GET /search/repositories?q={query}&sort=stars&per_page={max_results}` with bearer token. Maps `description` + top-level README first 1,000 chars to `body`.
- `rss`: Accepts a comma-separated list of feed URLs embedded in `query` as `feeds:<url1>,<url2> keyword:<term>`. Uses `feedparser.parse()` for each URL, filters entries whose title or summary contains the keyword, returns up to `max_results` entries.

**Agent integration:** The Generator Agent calls this tool during Phase 1 with three sequential invocations: `source=arxiv`, `source=github`, `source=rss`. Results are merged into a single `RawDocument` list before Phase 2.

---

### 2.2 `mcp-sql-tool`

**Purpose:** Parameterized read/write access to the primary SQLite database (`pulseboard.db`).

**Transport:** stdio

**Underlying library:** Python standard library `sqlite3`

**Tools registered:**

```
name:   query
input:  {
          "sql":    string,        // SELECT statement only
          "params": array | null   // positional bind parameters
        }
output: {
          "rows":    array,        // list of row dicts
          "row_count": integer
        }

name:   execute
input:  {
          "sql":    string,        // INSERT / UPDATE / DELETE / DDL
          "params": array | null
        }
output: {
          "rows_affected": integer,
          "last_insert_id": integer | null
        }
```

**Launch configuration:**

```
command: uv run python -m backend.mcp_servers.sql_server
args:    []
env:
  DATABASE_PATH: ./pulseboard.db   // resolved relative to backend/
```

**Security constraints enforced by the server, not the agent:**
- `query` tool: rejects any SQL that is not a `SELECT` statement (case-insensitive prefix check after stripping whitespace).
- `execute` tool: rejects `DROP TABLE`, `DROP DATABASE`, and `ATTACH DATABASE` statements.
- All statements use parameterized execution — the server never uses f-strings or `.format()` to build SQL.
- The server opens SQLite in WAL journal mode on startup: `PRAGMA journal_mode=WAL`.

**Agent integration:** The Generator Agent calls `query` during Phase 1 deduplication (`SELECT id FROM generator_documents WHERE url = ? OR content_hash = ?`). It calls `execute` during Phase 4 to insert the final `StoragePayload` and receive the `last_insert_id` as `Item_ID`.

---

### 2.3 `mcp-vector-tool`

**Purpose:** Semantic embedding storage and retrieval using ChromaDB in embedded (in-process) mode.

**Transport:** stdio

**Underlying library:** `chromadb` (embedded), `google-genai` for embedding generation via `models.embed_content`

**Tools registered:**

```
name:   upsert
input:  {
          "id":       string,          // Item_ID as string, e.g. "42"
          "text":     string,          // summary text to embed
          "metadata": object           // taxonomy_tags as array, plus any scalar fields
        }
output: {
          "id":      string,
          "status":  enum["created", "updated"]
        }

name:   search
input:  {
          "query_text": string,
          "filters":    object | null,  // ChromaDB `where` clause, e.g. {"taxonomy_tags": {"$contains": "AI Engineering"}}
          "top_k":      integer         // default 10
        }
output: {
          "results": [
            {
              "id":       string,
              "distance": float,
              "metadata": object
            }
          ]
        }
```

**Launch configuration:**

```
command: uv run python -m backend.mcp_servers.vector_server
args:    []
env:
  CHROMA_PERSIST_DIR: ./chroma_db      // relative to backend/
  GEMINI_API_KEY:     <from environment>
  CHROMA_COLLECTION:  generator_docs   // configurable
```

**Embedding model:** `models/text-embedding-004` via `google-genai`. This is Google's dedicated embedding model, not the generative flash model. Task type `RETRIEVAL_DOCUMENT` for upsert, `RETRIEVAL_QUERY` for search.

**Agent integration:** Called during Phase 4. The agent calls `upsert` with `id=str(Item_ID)`, `text=extracted_doc.summary`, and `metadata={"taxonomy_tags": extracted_doc.taxonomy_tags, "source": payload.source, "published_at": payload.published_at}`.

---

## 3. Celery Worker Structure

### Task Graph

```
Beat Scheduler
    |
    | fires every N hours per source
    v
harvest_task(source, query_params)     [queue: ingestion]
    |
    | returns list[RawDocument]
    v
gatekeeper_task(raw_doc)               [queue: llm]   -- one task per document, fanned out
    |
    | returns MetadataGatekeeperResult or None
    v
extractor_task(raw_doc)                [queue: llm]   -- only called if gatekeeper passed
    |
    | returns ExtractedDocument
    v
storage_router_task(extracted_doc)     [queue: ingestion]
    |
    | returns StoragePayload
    v
Done
```

`harvest_task` fans out by calling `gatekeeper_task.delay(doc)` for each surviving document in a loop. It does not use Celery `chord` or `group` because fan-out to `llm` queue must be rate-limited (see retry policy below). `extractor_task` is called inside `gatekeeper_task` upon pass — it is not a separate fan-out — to avoid an extra broker round-trip for a document that has already been loaded into memory.

### Queue Separation

**`ingestion` queue:** harvest and storage tasks. These tasks call MCP search and SQL tools. They are I/O-bound but not LLM-bound. Workers on this queue use Celery's default prefork pool with concurrency=4. No rate limit needed.

**`llm` queue:** gatekeeper and extractor tasks. These tasks make Gemini API calls. Workers on this queue must be rate-limited to respect the Gemini API quota. Set `task_annotations = {"generator.tasks.gatekeeper_task": {"rate_limit": "30/m"}, "generator.tasks.extractor_task": {"rate_limit": "10/m"}}` in Celery config. Concurrency=2 on this queue to avoid overwhelming the thread-pool when Gemini calls block.

### Pool Recommendation: Solo Pool for SQLite

The `mcp-sql-tool` server process holds an open SQLite connection. Because the server is launched as a subprocess per-worker, multiple Celery worker processes each launch their own `sql_server` subprocess with their own SQLite connection. SQLite in WAL mode supports concurrent readers and a single writer. This is safe as long as write serialization is acceptable.

**Verdict:** Use `--pool=solo` for the worker that processes `storage_router_task` on the `ingestion` queue. Solo pool means single-threaded execution on that worker, eliminating concurrent write contention entirely. The throughput bottleneck is Gemini API rate limits (30 req/min on `llm` queue), not SQLite write speed. A single-threaded storage worker is not the bottleneck.

For the `harvest_task` and `gatekeeper_task` workers, prefork pool is acceptable because their SQL calls are read-only (`query` tool, not `execute`).

### Beat Schedule

```python
beat_schedule = {
    "harvest-arxiv-6h": {
        "task": "generator.tasks.harvest_task",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": ["arxiv", {"query": "machine learning systems distributed", "max_results": 30}],
    },
    "harvest-github-12h": {
        "task": "generator.tasks.harvest_task",
        "schedule": crontab(minute=30, hour="*/12"),
        "args": ["github", {"query": "llm inference optimization", "max_results": 20}],
    },
    "harvest-rss-3h": {
        "task": "generator.tasks.harvest_task",
        "schedule": crontab(minute=15, hour="*/3"),
        "args": ["rss", {"query": "feeds:https://feeds.feedburner.com/oreilly/radar,https://engineeringblogs.xyz/feed.xml keyword:engineering", "max_results": 25}],
    },
}
```

Beat schedules are staggered by minute offset to avoid simultaneous LLM fanout spikes.

### How Celery Workers Invoke the Generator Agent

Each task that needs the Generator Agent calls `GeneratorAgent.run(phase, payload)`. `GeneratorAgent` is not an async class — it is a synchronous class that manages the stdio subprocesses for its MCP servers and runs a Gemini function-calling loop. Celery workers are synchronous by default; there is no `asyncio.run()` wrapper needed. The MCP subprocess stdio reads use blocking `subprocess.communicate()` per call.

```
CeleryWorker process
    |
    | calls GeneratorAgent(phase="gatekeeper").run(raw_doc)
    v
GeneratorAgent.__init__
    | launches mcp-sql-tool subprocess (for dedup check in harvest phase)
    | launches mcp-vector-tool subprocess (for storage phase)
    | creates Gemini client
    v
GeneratorAgent.run()
    | assembles initial prompt + tool manifest
    | enters function-calling loop (max 8 iterations)
    | on STOP_SEQUENCE or no more tool calls: returns result dict
    v
CeleryWorker receives typed result, chains to next task
```

The Generator Agent launches only the MCP servers it needs for its phase:
- Phase 1 (harvest): `mcp-search-tool` + `mcp-sql-tool`
- Phase 2 (gatekeeper): no MCP tools — pure Gemini call, no subprocess needed
- Phase 3 (extractor): no MCP tools — pure Gemini call
- Phase 4 (storage): `mcp-sql-tool` + `mcp-vector-tool`

### Error Handling and Retry Policy

| Task | Max Retries | Retry Delay | On Final Failure |
|---|---|---|---|
| `harvest_task` | 3 | exponential: 60s, 300s, 900s | log error, emit metric, skip batch |
| `gatekeeper_task` | 2 | 30s, 120s | discard document, log warning |
| `extractor_task` | 2 | 60s, 300s | discard document, log error |
| `storage_router_task` | 5 | 10s, 30s, 60s, 120s, 300s | dead-letter queue, alert |

`storage_router_task` gets the most retries because a document that has already passed Phases 1-3 has consumed LLM tokens. Discarding it at storage is wasteful and should be retried aggressively. If all retries fail, the task payload is written to a `dead_letter_storage` Redis key for manual replay.

MCP tool errors (non-zero exit code from subprocess or malformed JSON-RPC response) cause the Generator Agent to raise `MCPToolError`. All Celery tasks catch `MCPToolError` and treat it as a retryable error using `self.retry(exc=exc)`.

---

## 4. Pydantic Schemas

These are the complete, typed schema definitions. These go in `backend/generator/schemas.py`.

```python
from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DataSource(str, Enum):
    ARXIV = "arxiv"
    GITHUB = "github"
    RSS = "rss"


# ---------------------------------------------------------------------------
# Phase 1 Output
# ---------------------------------------------------------------------------


class RawDocument(BaseModel):
    """Output of Phase 1: a single harvested document after heuristic filtering."""

    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1)
    body: str = Field(..., description="Raw full text or abstract")
    author: str = Field(default="Unknown")
    published_at: str = Field(description="ISO 8601 date string or empty string")
    source: DataSource

    @computed_field  # type: ignore[prop-decorator]
    @property
    def content_hash(self) -> str:
        """SHA-256 of url + body[:1000]. Used for deduplication in mcp-sql-tool."""
        digest_input = self.url + self.body[:1000]
        return hashlib.sha256(digest_input.encode()).hexdigest()

    @model_validator(mode="after")
    def enforce_word_count(self) -> RawDocument:
        word_count = len(self.body.split())
        if word_count < 300:
            raise ValueError(
                f"Body too short ({word_count} words < 300 minimum). Discard."
            )
        return self

    @model_validator(mode="after")
    def enforce_no_spam_title(self) -> RawDocument:
        import re
        spam_patterns = [
            r"(?i)^top\s+\d+",
            r"(?i)ultimate\s+guide",
            r"(?i)you\s+won'?t\s+believe",
            r"(?i)best\s+\d+\s+tools",
            r"(?i)complete\s+guide\s+to",
        ]
        for pattern in spam_patterns:
            if re.search(pattern, self.title):
                raise ValueError(
                    f"Title matches spam pattern: {pattern!r}. Discard."
                )
        return self


# ---------------------------------------------------------------------------
# Phase 2 LLM Output
# ---------------------------------------------------------------------------


class MetadataGatekeeperResult(BaseModel):
    """JSON output from gemini-2.5-flash-lite in Phase 2 (Metadata Gatekeeper)."""

    is_high_signal: bool
    confidence: float = Field(..., ge=0.0, le=1.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passes(self) -> bool:
        """True only if both conditions are satisfied."""
        return self.is_high_signal and self.confidence >= 0.8


# ---------------------------------------------------------------------------
# Phase 3 LLM Output
# ---------------------------------------------------------------------------


TAXONOMY_TAGS: frozenset[str] = frozenset(
    [
        "AI Engineering",
        "Machine Learning",
        "Data Analytics",
        "Distributed Systems",
        "Cloud Infrastructure",
        "Developer Tooling",
        "Security Engineering",
        "Database Systems",
        "API Design",
        "Observability",
        "Open Source",
        "Systems Programming",
        "Web Engineering",
        "Mobile Engineering",
        "Platform Engineering",
        "Edge Computing",
    ]
)


class ExtractedDocument(BaseModel):
    """JSON output from gemini-2.5-flash in Phase 3 (Deep Extractor)."""

    summary: str = Field(..., min_length=1, max_length=1000)
    bm25_keywords: list[str] = Field(..., min_length=5, max_length=10)
    taxonomy_tags: list[str] = Field(..., min_length=1, max_length=3)
    image_url: str = Field(default="")

    @model_validator(mode="after")
    def validate_taxonomy_tags(self) -> ExtractedDocument:
        invalid = [t for t in self.taxonomy_tags if t not in TAXONOMY_TAGS]
        if invalid:
            raise ValueError(
                f"Taxonomy tags not in closed vocabulary: {invalid}. "
                f"Valid tags: {sorted(TAXONOMY_TAGS)}"
            )
        return self


# ---------------------------------------------------------------------------
# Phase 4 Router Input
# ---------------------------------------------------------------------------


class StoragePayload(BaseModel):
    """Assembled payload sent to storage_router_task. Contains all phases combined."""

    # Provenance
    url: str
    content_hash: str
    source: DataSource
    author: str
    published_at: str
    title: str

    # Phase 3 extracted data
    summary: str
    bm25_keywords: list[str]
    taxonomy_tags: list[str]
    image_url: str

    # Filled in by storage_router_task after mcp-sql-tool insert
    item_id: int | None = Field(default=None)
    embedding_id: str | None = Field(
        default=None,
        description="ChromaDB document ID; equals str(item_id) after upsert",
    )
    fts_rowid: int | None = Field(
        default=None,
        description="SQLite FTS5 rowid for the BM25 sparse index entry",
    )
    stored_at: datetime | None = Field(default=None)


# ---------------------------------------------------------------------------
# MCP Tool Call / Result Logging
# ---------------------------------------------------------------------------


class MCPToolCall(BaseModel):
    """Records a single tool invocation made by the Generator Agent. Persisted for audit."""

    tool_name: str = Field(..., description="e.g. 'search', 'query', 'upsert'")
    server: str = Field(..., description="e.g. 'mcp-search-tool'")
    input_params: dict[str, Any]
    called_at: datetime
    task_id: str = Field(..., description="Celery task ID for correlation")


class MCPToolResult(BaseModel):
    """Response from an MCP server. Paired with MCPToolCall by task_id + tool_name."""

    tool_name: str
    server: str
    output: dict[str, Any]
    error: str | None = Field(default=None)
    duration_ms: float
    responded_at: datetime
    task_id: str
```

---

## 5. Taxonomy Design

### Complete Tag Vocabulary

The following 16 tags form the closed vocabulary for Phase 3. They are designed to cover the intersection of PulseBoard's user base (engineers, researchers, technical PMs) and the sources ingested (ArXiv, GitHub, engineering RSS):

| Tag | Covers |
|---|---|
| AI Engineering | LLM deployment, inference optimization, RAG pipelines, model serving |
| Machine Learning | Training, fine-tuning, evaluation, model architectures (non-infra angle) |
| Data Analytics | Data pipelines, warehousing, BI tooling, Spark/Flink/dbt |
| Distributed Systems | Consensus, replication, CAP theorem, message queues, coordination |
| Cloud Infrastructure | AWS/GCP/Azure specifics, IaC (Terraform), Kubernetes, FinOps |
| Developer Tooling | IDEs, CLI tools, build systems, package managers, code generation |
| Security Engineering | Zero trust, CVEs, secret management, SAST/DAST, supply chain |
| Database Systems | OLTP/OLAP engines, query optimization, storage formats, migrations |
| API Design | REST, gRPC, GraphQL, AsyncAPI, contract-first, gateway patterns |
| Observability | Tracing, metrics, logging, SLOs, alerting, OpenTelemetry |
| Open Source | OSS governance, release announcements, community activity |
| Systems Programming | Rust, C/C++, memory management, low-level OS primitives |
| Web Engineering | Browsers, JS runtimes, React/Vue ecosystem, web perf |
| Mobile Engineering | iOS/Android, cross-platform, app performance |
| Platform Engineering | Internal developer platforms, golden paths, self-service infra |
| Edge Computing | CDN edge functions, WASM, IoT, latency-sensitive deployment |

16 tags intentionally avoids being too fine-grained (which makes the LLM inconsistent) or too coarse (which makes retrieval filters useless). The vocabulary is defined in `TAXONOMY_TAGS` in `generator/schemas.py` as a `frozenset[str]` — it is the single source of truth referenced by both the Pydantic validator and the Phase 3 prompt.

### How the Prompt Constrains to Closed Vocabulary

The Phase 3 extractor prompt includes the tag list verbatim:

```
You must assign 1-3 taxonomy_tags from this exact closed list. No other values are permitted:
["AI Engineering", "Machine Learning", "Data Analytics", "Distributed Systems",
 "Cloud Infrastructure", "Developer Tooling", "Security Engineering", "Database Systems",
 "API Design", "Observability", "Open Source", "Systems Programming",
 "Web Engineering", "Mobile Engineering", "Platform Engineering", "Edge Computing"]

If the document does not clearly fit any tag, assign the single closest tag rather than
inventing a new one. Output ONLY valid JSON.
```

The `ExtractedDocument.validate_taxonomy_tags` validator in the Pydantic schema catches any hallucinated tags and raises a `ValueError`. The Generator Agent treats a Pydantic validation failure on the LLM output as a retryable error (re-prompt with the validation error message appended, up to 2 retries before discarding the document).

### Usage as ChromaDB Metadata Filters

ChromaDB metadata filters use the `where` clause syntax. At retrieval time (future retrieval API, not in scope for this TDD's implementation phase), the query becomes:

```python
collection.query(
    query_texts=["semantic query from user profile"],
    n_results=20,
    where={"taxonomy_tags": {"$contains": "AI Engineering"}},
)
```

Because ChromaDB metadata values must be scalars or lists of scalars, `taxonomy_tags` is stored as a JSON-serialized list string in the metadata dict: `{"taxonomy_tags_json": '["AI Engineering", "Distributed Systems"]'}`. The `$contains` operator on a string field uses substring matching. The `mcp-vector-tool` server handles this serialization internally — the agent always passes `taxonomy_tags` as a Python list in the `upsert` call's `metadata` field.

---

## 6. Generator Agent Architecture

### Agent Loop Design

The Generator Agent is a **structured function-calling loop** using the Gemini function calling API (`google-genai` SDK). It is not a ReAct (Reasoning + Acting) agent with free-form chain-of-thought. The loop is bounded and deterministic: each phase has a fixed maximum number of iterations (harvest: 6, storage: 4) and a fixed set of permissible tool calls.

**Verdict on API choice:** Use Gemini's native function calling API (`tools=` parameter in `GenerateContentConfig`) rather than Claude's `tool_use` API. Rationale: the project already uses `google-genai` SDK; adding the Anthropic SDK solely for the agent loop doubles the LLM vendor surface, adds latency (different API endpoint), and creates a cost model with two billing relationships. Gemini's function calling is functionally equivalent to Claude's `tool_use` for this bounded use case.

### Agent Loop Pseudocode

```
GeneratorAgent.run(phase, payload):
    messages = [system_prompt(phase), user_message(payload)]
    tool_manifest = tools_for_phase(phase)
    iteration = 0

    while iteration < MAX_ITERATIONS[phase]:
        response = gemini.generate_content(
            contents=messages,
            config=GenerateContentConfig(tools=tool_manifest)
        )

        if response has no function_calls:
            # Model produced a final text response — extract structured JSON
            return parse_final_output(response.text, phase)

        for function_call in response.function_calls:
            tool_result = dispatch_to_mcp_server(function_call)
            log_mcp_tool_call(function_call, tool_result)  # MCPToolCall + MCPToolResult
            messages.append(function_call_to_content(function_call))
            messages.append(tool_result_to_content(tool_result))

        iteration += 1

    raise AgentLoopExhaustedError(f"Phase {phase} exceeded {MAX_ITERATIONS[phase]} iterations")
```

`MAX_ITERATIONS`: `{"harvest": 6, "gatekeeper": 1, "extractor": 1, "storage": 4}`

Gatekeeper and extractor have `MAX_ITERATIONS=1` because they make no MCP tool calls — they receive the full document as a user message and return structured JSON in a single generation. The loop still wraps them for uniformity and error handling.

### Tool Dispatch

`dispatch_to_mcp_server(function_call)` maps tool names to their server subprocess:

```
search  ->  mcp-search-tool subprocess stdin
query   ->  mcp-sql-tool subprocess stdin
execute ->  mcp-sql-tool subprocess stdin
upsert  ->  mcp-vector-tool subprocess stdin
search (vector context)  ->  mcp-vector-tool subprocess stdin
```

The disambiguation between `search` (web) and `search` (vector) is resolved by name-qualifying the tools in the manifest: `search_web` and `search_vectors`. The MCP server tool registrations use these unambiguous names.

### MCP Tool Error Handling

| Error Type | Agent Behavior |
|---|---|
| MCP server subprocess crash | Restart subprocess, retry tool call once, then raise `MCPToolError` to Celery |
| Malformed JSON-RPC response | Log full response bytes, raise `MCPToolError` immediately (no retry — corrupt state) |
| Tool-level error in response (`"error"` key present) | Log error, increment retry counter, re-emit same tool call if < 2 retries, else skip document |
| MCP server returns empty results for `search_web` | Agent proceeds with 0 documents — harvest task returns empty list, no error raised |
| `mcp-sql-tool execute` returns `rows_affected=0` | Agent raises `StorageInsertError` — triggers Celery retry |

---

## 7. Integration with Existing Code

### Relationship to `agents/research_agent.py`

No changes. `research_agent.py` remains the production handler for `GET /feed/{user_id}` and `GET /events/{user_id}`. It uses DuckDuckGo, calls Gemini directly, and returns user-scoped feed items. It is purpose-built for low-latency, on-demand, user-personalized generation.

The Generator Agent (this TDD) runs on a separate scheduled background pipeline. Its output lands in `generator_documents` — a separate table from `feed_items`. The two pipelines do not share a table, a Celery queue, or a module. Future work may add a `GET /discover` endpoint that queries `generator_documents` for personalized retrieval, but that is outside this TDD's scope.

### Relationship to `routes/feed.py` and `FeedItem`

No changes. `routes/feed.py` continues to import from `agents.research_agent`. The Generator Agent pipeline has no FastAPI route in Phase 1 — it is triggered exclusively by Celery Beat.

### `generator_documents` Table — Full DDL

```sql
-- Primary storage for all ingested documents
CREATE TABLE IF NOT EXISTS generator_documents (
    id              INTEGER  PRIMARY KEY AUTOINCREMENT,
    url             TEXT     NOT NULL,
    content_hash    TEXT     NOT NULL,
    source          TEXT     NOT NULL CHECK(source IN ('arxiv', 'github', 'rss')),
    author          TEXT     NOT NULL DEFAULT 'Unknown',
    published_at    TEXT     NOT NULL DEFAULT '',
    title           TEXT     NOT NULL,
    summary         TEXT     NOT NULL,
    taxonomy_tags   TEXT     NOT NULL DEFAULT '[]',  -- JSON array stored as text
    image_url       TEXT     NOT NULL DEFAULT '',
    embedding_id    TEXT,                            -- ChromaDB document ID (str(id))
    fts_rowid       INTEGER,                         -- rowid in generator_docs_fts
    ingested_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_generator_url          UNIQUE (url),
    CONSTRAINT uq_generator_content_hash UNIQUE (content_hash)
);

CREATE INDEX IF NOT EXISTS idx_generator_docs_source
    ON generator_documents(source);

CREATE INDEX IF NOT EXISTS idx_generator_docs_ingested_at
    ON generator_documents(ingested_at DESC);

-- Sparse BM25 full-text search index
-- title and bm25_keywords columns are tokenized by FTS5
CREATE VIRTUAL TABLE IF NOT EXISTS generator_docs_fts
    USING fts5(
        title,
        bm25_keywords,
        content='generator_documents',
        content_rowid='id'
    );

-- Keep FTS index in sync via triggers
CREATE TRIGGER IF NOT EXISTS generator_docs_fts_insert
    AFTER INSERT ON generator_documents BEGIN
        INSERT INTO generator_docs_fts(rowid, title, bm25_keywords)
        VALUES (new.id, new.title, new.bm25_keywords);
    END;

CREATE TRIGGER IF NOT EXISTS generator_docs_fts_delete
    AFTER DELETE ON generator_documents BEGIN
        INSERT INTO generator_docs_fts(generator_docs_fts, rowid, title, bm25_keywords)
        VALUES ('delete', old.id, old.title, old.bm25_keywords);
    END;

-- MCP tool call audit log
CREATE TABLE IF NOT EXISTS mcp_tool_audit (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    task_id     TEXT     NOT NULL,
    tool_name   TEXT     NOT NULL,
    server      TEXT     NOT NULL,
    input_json  TEXT     NOT NULL,
    output_json TEXT,
    error       TEXT,
    duration_ms REAL     NOT NULL,
    called_at   DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mcp_audit_task_id
    ON mcp_tool_audit(task_id);

CREATE INDEX IF NOT EXISTS idx_mcp_audit_called_at
    ON mcp_tool_audit(called_at DESC);
```

Note: `bm25_keywords` in `generator_docs_fts` is stored as a space-joined string (e.g., `"transformer inference quantization gguf llama"`), produced by `" ".join(extracted_doc.bm25_keywords)` before the FTS insert.

### Migration Strategy

Add to `_run_migrations()` in `main.py` using the existing pattern (raw SQL wrapped in `try/except OperationalError`):

```python
# generator_documents and FTS table
"CREATE TABLE IF NOT EXISTS generator_documents (...)",
"CREATE INDEX IF NOT EXISTS idx_generator_docs_source ON generator_documents(source)",
"CREATE INDEX IF NOT EXISTS idx_generator_docs_ingested_at ON generator_documents(ingested_at DESC)",
"CREATE VIRTUAL TABLE IF NOT EXISTS generator_docs_fts USING fts5(...)",
"CREATE TRIGGER IF NOT EXISTS generator_docs_fts_insert ...",
"CREATE TRIGGER IF NOT EXISTS generator_docs_fts_delete ...",
"CREATE TABLE IF NOT EXISTS mcp_tool_audit (...)",
"CREATE INDEX IF NOT EXISTS idx_mcp_audit_task_id ON mcp_tool_audit(task_id)",
"CREATE INDEX IF NOT EXISTS idx_mcp_audit_called_at ON mcp_tool_audit(called_at DESC)",
```

Because all DDL statements use `IF NOT EXISTS`, they are idempotent on re-run. The `try/except OperationalError` wrapper in `_run_migrations()` already handles this case.

---

## 8. File and Module Layout

```
backend/
├── main.py                           (existing — add migration DDL only)
├── database.py                       (existing — no changes)
├── models.py                         (existing — no changes)
├── schemas.py                        (existing — no changes)
├── auth.py                           (existing — no changes)
├── routes/                           (existing — no changes)
│   ├── users.py
│   ├── feed.py
│   └── events.py
│
├── agents/                           (existing — no changes)
│   └── research_agent.py
│
├── generator/                        (NEW package)
│   ├── __init__.py
│   ├── schemas.py                    -- Pydantic models from Section 4
│   ├── agent.py                      -- GeneratorAgent class (tool-calling loop)
│   ├── tasks.py                      -- Celery task definitions
│   ├── celery_app.py                 -- Celery app instance + config
│   ├── prompts.py                    -- Phase 2 and Phase 3 prompt templates
│   └── exceptions.py                 -- MCPToolError, AgentLoopExhaustedError, StorageInsertError
│
├── mcp_servers/                      (NEW package)
│   ├── __init__.py
│   ├── base.py                       -- JSON-RPC stdio loop, MCPServer base class
│   ├── search_server.py              -- mcp-search-tool (arxiv + github + rss)
│   ├── sql_server.py                 -- mcp-sql-tool (sqlite3 wrapper)
│   └── vector_server.py              -- mcp-vector-tool (chromadb + embedding)
│
└── tests/
    ├── conftest.py                   (existing)
    ├── test_auth.py                  (existing)
    ├── test_users.py                 (existing)
    ├── test_feed.py                  (existing)
    ├── test_events.py                (existing)
    ├── test_agents.py                (existing)
    │
    ├── generator/                    (NEW)
    │   ├── __init__.py
    │   ├── test_schemas.py           -- RawDocument heuristic validators, ExtractedDocument taxonomy validation
    │   ├── test_agent.py             -- GeneratorAgent loop with mock MCP servers
    │   ├── test_tasks.py             -- Celery tasks with mocked GeneratorAgent
    │   └── test_storage_router.py   -- storage_router_task SQL insert + FTS trigger
    │
    └── mcp_servers/                  (NEW)
        ├── __init__.py
        ├── test_search_server.py     -- JSON-RPC protocol tests with mock arxiv/github/feedparser
        ├── test_sql_server.py        -- query/execute tools, injection prevention, WAL mode
        └── test_vector_server.py     -- upsert/search with mock chromadb collection
```

**Key design decisions in this layout:**

- `generator/` and `mcp_servers/` are sibling packages under `backend/`. Neither imports from the other directly — `generator/agent.py` communicates with MCP servers via subprocess stdio, not Python imports.
- `mcp_servers/base.py` provides the reusable stdio JSON-RPC loop so each server module only needs to define its tool handlers.
- `generator/prompts.py` isolates all LLM prompt strings. This makes A/B testing prompt variants easy without touching agent logic.
- Test directories mirror the source layout. `tests/generator/` tests task logic with mocked agents; `tests/mcp_servers/` tests the server protocol in isolation.

---

## 9. Dependency Manifest

All additions to `backend/pyproject.toml`. Existing dependencies (`fastapi`, `sqlalchemy`, `google-genai`, etc.) are unchanged.

```toml
[project]
dependencies = [
    # --- existing ---
    "ddgs>=9.11.4",
    "fastapi>=0.135.1",
    "google-genai>=1.68.0",
    "passlib[bcrypt]>=1.7.4",
    "pydantic>=2.12.5",
    "python-dotenv>=1.2.2",
    "python-jose[cryptography]>=3.5.0",
    "sqlalchemy>=2.0.48",
    "uvicorn>=0.42.0",

    # --- new: task queue ---
    "celery>=5.4.0",
    # Rationale: Celery 5.4 is the stable release line for Python 3.13.
    # Provides task routing, beat scheduler, retry policies, and rate limiting.
    # No Django dependency.

    "redis>=5.0.0",
    # Rationale: Celery broker and result backend. Redis is the standard choice
    # over RabbitMQ for a single-developer project: easier to run locally (Docker),
    # supports pub/sub for future real-time features, and has a simple data model.
    # The `redis-py` v5 client is compatible with Python 3.13 without deprecation warnings.

    # --- new: MCP search server ---
    "arxiv>=2.1.0",
    # Rationale: Official arxiv Python SDK. Provides Search, Result, and pagination
    # abstractions over the ArXiv API v2. Stable, maintained by Cornell.

    "feedparser>=6.0.11",
    # Rationale: Industry-standard RSS/Atom parser. Handles malformed feeds gracefully.
    # Version 6.x is Python 3 native with no chardet dependency.

    "httpx>=0.27.0",
    # Rationale: Already in dev dependencies (via pytest). Promoting to production
    # dependency for GitHub API calls in search_server.py. Async-capable, modern
    # replacement for requests, built-in timeout support.

    # --- new: MCP vector server ---
    "chromadb>=0.6.0",
    # Rationale: ChromaDB in embedded (in-process) mode requires no external server.
    # This eliminates an operational dependency during development. v0.6 ships with
    # the HNSW index backed by hnswlib, DuckDB removed, SQLite-backed persistence.
    # The embedded mode is the correct choice for a single-server deployment.
    # Trade-off: embedded mode does not support multi-process concurrent writes.
    # This is acceptable because the vector server runs as a single subprocess
    # per worker (see Solo pool recommendation in Section 3).
]

[dependency-groups]
dev = [
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "types-python-jose>=3.3.4",

    # --- new dev dependencies ---
    "celery[pytest]>=5.4.0",
    # Rationale: pytest-celery fixtures for task unit tests without a live broker.

    "fakeredis>=2.26.0",
    # Rationale: In-memory Redis replacement for Celery tests. No Docker required
    # in CI. Compatible with redis-py v5.
]
```

**What is deliberately not added:**

- `anthropic` SDK: not needed, Gemini function calling is used for the agent loop.
- `langchain` or `llamaindex`: unnecessary abstraction layer that hides MCP mechanics. The Generator Agent loop is under 80 lines of code — a framework adds more complexity than it removes.
- `alembic`: the existing `_run_migrations()` raw SQL pattern in `main.py` is sufficient for this project's scale. Alembic would be the correct choice if the team grew beyond 2 engineers.
- `sentence-transformers`: Google's `text-embedding-004` via `google-genai` is already available and avoids adding a 1.5GB PyTorch dependency.

---

## 10. Risk and Trade-off Analysis

### MCP Overhead vs. Direct Library Calls

**Latency cost:** Each MCP tool call adds one subprocess stdin write, one stdout read, and two JSON serializations. On a local machine this is approximately 2-5ms per call. For the harvest phase with ~6 tool calls, this adds 12-30ms to a pipeline that otherwise takes 3-8 seconds per document (dominated by Gemini API latency). The overhead is below 1% of total task time.

**Added complexity:** The MCP architecture adds three server files, a base class, and a JSON-RPC protocol layer that would not exist in a direct-call design. The breakeven point for this complexity is when you need to swap a tool implementation or run integration tests against a mock server. For a solo-developer portfolio project, this breakeven may never arrive. The architectural purity is real but so is the cost.

**Verdict:** The MCP layer is architecturally justified for this TDD's stated requirements. For a minimum viable first deployment, `harvest_task` could call the Python libraries directly and be refactored to MCP invocations in a second pass with no changes to `gatekeeper_task`, `extractor_task`, or `storage_router_task`.

**Debugging surface:** MCP errors produce opaque subprocess failures. The `mcp_tool_audit` table mitigates this by logging every tool call with full input/output JSON. When a pipeline fails, `SELECT * FROM mcp_tool_audit WHERE task_id = '...' ORDER BY called_at` shows exactly what the agent did.

---

### SQLite Write Contention

The `mcp-sql-tool` server enables WAL mode, which allows concurrent reads alongside a single writer. Under the proposed architecture, only `storage_router_task` calls `execute`. With `--pool=solo` on the ingestion worker handling storage tasks, writes are serialized at the Celery worker level. There is no concurrent write contention.

However, if the deployment scales to multiple Celery workers on separate machines sharing a network-mounted SQLite file, WAL mode breaks and write locks will timeout. This is the hard ceiling of SQLite as a write backend.

**Verdict:** SQLite is acceptable for the current single-server deployment. The `storage_router_task` retry policy (5 retries with exponential backoff) absorbs the occasional WAL write lock timeout. When the ingestion rate exceeds ~100 documents/hour sustained, migrate the `mcp-sql-tool` to wrap PostgreSQL instead of SQLite — this requires changing `sql_server.py` only, not the agent.

---

### Gemini Function Calling vs. Claude `tool_use`

| Dimension | Gemini Function Calling | Claude `tool_use` |
|---|---|---|
| SDK already in project | Yes (`google-genai`) | No (requires `anthropic`) |
| Supported model | `gemini-2.5-flash` | `claude-sonnet-4-6` |
| Cost per 1M input tokens | Lower (Flash pricing) | Higher (Sonnet pricing) |
| Tool call JSON schema | OpenAPI subset | Anthropic schema |
| Parallel tool calls in one turn | Yes (Gemini supports multi-function in one response) | Yes |
| Context window | 1M tokens | 200K tokens |

**Verdict:** Use Gemini function calling. The existing SDK, lower cost, and larger context window are decisive for a pipeline that may pass multi-page documents. The only scenario where Claude `tool_use` would be preferred is if Claude's reasoning quality on tool selection is measurably better — which should be validated empirically, not assumed.

---

### Cost Estimate per 1,000 Documents

Assumptions: average document body = 2,000 tokens, average summary = 150 tokens. Gemini pricing as of Q1 2026 (verify current rates at ai.google.dev/pricing before implementation).

| Phase | Model | Input tokens | Output tokens | Cost per doc | Cost per 1K docs |
|---|---|---|---|---|---|
| Phase 2 Gatekeeper | `gemini-2.5-flash-lite` | ~600 (title + 500 chars) | ~50 | ~$0.00003 | ~$0.03 |
| Phase 3 Extractor | `gemini-2.5-flash` | ~2,100 (full body) | ~200 | ~$0.0007 | ~$0.70 |
| Embedding (upsert) | `text-embedding-004` | ~200 (summary) | n/a | ~$0.000003 | ~$0.003 |

**Total: approximately $0.73 per 1,000 documents**, assuming a 50% gatekeeper pass rate (500 documents reach Phase 3).

The dominant cost is Phase 3 extraction on `gemini-2.5-flash`. If budget is constrained, Phase 3 can be tested on `gemini-2.5-flash-lite` first — the quality difference for structured JSON extraction from technical text is often negligible compared to the 10x cost reduction.

---

### What Breaks if `mcp-vector-tool` Goes Down Mid-Pipeline

The vector server going down affects only the `upsert` call in `storage_router_task`. The SQL insert into `generator_documents` has already completed at that point (`item_id` is populated). The document is durably stored in SQLite with `embedding_id = NULL`.

Recovery path:
1. `storage_router_task` catches `MCPToolError` on the `upsert` call and retries up to 5 times.
2. If all retries fail, the task completes without error (it logs a warning) — the document is in SQL but not in ChromaDB.
3. A separate maintenance task `backfill_embeddings_task` (not in this TDD's scope but trivial to add) queries `SELECT id, summary, taxonomy_tags FROM generator_documents WHERE embedding_id IS NULL` and replays the `upsert` calls. This can run on the next Beat schedule.

**The SQLite table is the source of truth. ChromaDB is a derived index.** This is why Phase 4 performs the SQL insert before the vector upsert, not after. A document with `embedding_id = NULL` is invisible to semantic search but fully recoverable. A document that was embedded but not SQL-inserted would have a dangling ChromaDB record with no referent — the opposite failure mode, which is harder to detect and recover from.

---

## Appendix A: Architecture Diagram

```
                        CELERY BEAT SCHEDULER
                              |
              +---------------+---------------+
              |               |               |
        arxiv/6h          github/12h       rss/3h
              |               |               |
              +-------+-------+---------------+
                      |
              [harvest_task] (queue: ingestion)
                      |
                      | launches subprocess
                      v
              mcp-search-tool server
              (arxiv SDK / httpx / feedparser)
                      |
                      | RawDocument list
                      v
              [heuristic filter]
              word_count >= 300, no spam title
                      |
              [dedup check via mcp-sql-tool]
              SELECT id WHERE url=? OR content_hash=?
                      |
                      | surviving RawDocuments
                      v
            +---------+---------+
            |         |         |  fan-out
     [gatekeeper_task x N]        (queue: llm)
            |
            | gemini-2.5-flash-lite
            | title + first 500 chars
            |
            | MetadataGatekeeperResult
            | passes = is_high_signal AND confidence >= 0.8
            |
     [extractor_task]  (inline, same task)
            |
            | gemini-2.5-flash
            | full document body
            |
            | ExtractedDocument
            | summary, bm25_keywords, taxonomy_tags
            |
     [storage_router_task]  (queue: ingestion)
            |
       +----+----+
       |         |
  mcp-sql-tool   mcp-vector-tool
  INSERT         upsert(id, summary, taxonomy_tags)
  generator_     chromadb collection
  documents      text-embedding-004
       |         |
       |    StoragePayload
       |    item_id, embedding_id, fts_rowid
       |
  FTS5 trigger fires automatically on INSERT
  generator_docs_fts updated
       |
     Done


SEPARATE PIPELINE (existing, no changes):
FastAPI GET /feed/{user_id}
    |
research_agent.py
    |
DuckDuckGo + Gemini
    |
feed_items table (user-scoped)
```

---

## Appendix B: Observability Hooks

Every Celery task must emit the following before returning:

**Structured log fields (JSON format, emitted via `structlog` or Python `logging` with JSON formatter):**
```json
{
  "event": "task_complete",
  "task": "harvest_task",
  "task_id": "abc-123",
  "source": "arxiv",
  "docs_harvested": 28,
  "docs_after_dedup": 19,
  "docs_after_heuristic": 15,
  "duration_ms": 4200,
  "trace_id": "propagated from FastAPI if triggered via API"
}
```

**Prometheus metrics** (expose via `prometheus-client` on a `/metrics` endpoint on the Celery worker, or push to Pushgateway):
- `generator_documents_ingested_total{source, taxonomy_tag}` — counter
- `generator_gatekeeper_pass_rate{source}` — gauge (passes / attempts per beat cycle)
- `generator_task_duration_seconds{task_name}` — histogram, buckets [0.5, 1, 2, 5, 15, 60]
- `generator_mcp_tool_errors_total{server, tool_name}` — counter

**Health check:** The Celery worker exposes a `/ready` endpoint via a dedicated FastAPI micro-app (`generator/health_app.py`) that checks Redis connectivity and the last successful `harvest_task` timestamp from the `mcp_tool_audit` table. If the last harvest is older than 2x the beat schedule interval, readiness returns 503.
```
