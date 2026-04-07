"""
PulseGen Admin API
------------------
Internal FastAPI admin console backend (port 8001).
Serves read-only operational data to the pulsegen/web admin console.

CORS is restricted to pulsegen_web (port 3001) and localhost.

Endpoints:
  GET  /admin/stats           — pipeline document counts, by_source, by_taxonomy
  GET  /admin/sources         — per-connector quality records (pass rates, last harvest)
  GET  /admin/pipeline/status — Celery queue depth + current phase
  POST /admin/pipeline/run-now — manually trigger harvest_cycle task
  GET  /admin/trends/keywords — recent batch of extracted trend keywords
  GET  /admin/trends/runs     — run metadata (collected_at, docs_analyzed count)
  GET  /admin/dead-letter     — failed document queue (Redis)
  POST /admin/dead-letter/{index}/retry — re-queue one failed item
  DELETE /admin/dead-letter   — flush entire dead-letter queue
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)

_TABLE_DDL = """
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS generator_documents (
        id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
        source                TEXT        NOT NULL,
        source_id             TEXT,
        url                   TEXT        NOT NULL,
        url_hash              TEXT        NOT NULL UNIQUE,
        content_hash          TEXT        NOT NULL,
        title                 TEXT        NOT NULL,
        author                TEXT,
        published_at          TIMESTAMPTZ,
        summary               TEXT        NOT NULL DEFAULT '',
        bm25_keywords         TEXT[]      NOT NULL DEFAULT '{}',
        taxonomy_tags         TEXT        NOT NULL DEFAULT '[]',
        image_url             TEXT        NOT NULL DEFAULT '',
        gatekeeper_confidence FLOAT       NOT NULL DEFAULT 0.0,
        pipeline_status       TEXT        NOT NULL DEFAULT 'stored',
        processed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        embedding             vector(768)
    );
    CREATE INDEX IF NOT EXISTS idx_gendocs_source ON generator_documents(source);
    CREATE INDEX IF NOT EXISTS idx_gendocs_processed_at ON generator_documents(processed_at DESC);
    CREATE INDEX IF NOT EXISTS idx_gendocs_url_hash ON generator_documents(url_hash);
"""


def _bootstrap_db() -> None:
    """Ensure generator_documents table exists on startup."""
    db_url = os.environ.get("STORAGE_DATABASE_URL", "")
    if not db_url:
        logger.warning("STORAGE_DATABASE_URL not set — skipping DB bootstrap")
        return
    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=5)
        conn.autocommit = True
        with conn.cursor() as cur:
            for statement in _TABLE_DDL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    cur.execute(stmt)
        conn.close()
        logger.info("generator_documents table ready")
    except Exception as exc:
        logger.warning("DB bootstrap warning: %s", exc)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    _bootstrap_db()
    yield

# CORS: restricted to pulsegen_web (3001) and localhost
_ALLOWED_ORIGINS = [
    "http://localhost:3001",
    "http://localhost:3000",
    "http://localhost",
    *([o.strip() for o in os.environ.get("PULSEGEN_ADMIN_ALLOWED_ORIGIN", "").split(",")]
      if os.environ.get("PULSEGEN_ADMIN_ALLOWED_ORIGIN") else []),
]

app = FastAPI(title="PulseGen Admin API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Import and register routers
from .dependencies import require_admin_key  # noqa: E402
from .routes import dead_letter, pipeline, sources, stats, trends  # noqa: E402

_auth = [Depends(require_admin_key)]

app.include_router(stats.router, prefix="/admin", dependencies=_auth)
app.include_router(sources.router, prefix="/admin", dependencies=_auth)
app.include_router(pipeline.router, prefix="/admin", dependencies=_auth)
app.include_router(trends.router, prefix="/admin", dependencies=_auth)
app.include_router(dead_letter.router, prefix="/admin", dependencies=_auth)


@app.get("/health")
def health() -> dict[str, object]:
    """
    Liveness + readiness probe.

    Checks Redis PING and PostgreSQL connectivity.
    Returns HTTP 200 always so load balancers keep routing; individual
    service status is surfaced in the JSON body so monitors can alert.
    """
    redis_ok = False
    postgres_ok = False

    # Redis probe
    try:
        import redis as redis_lib
        r = redis_lib.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=2,
        )
        r.ping()
        redis_ok = True
    except Exception as exc:
        logger.warning("Health: Redis unreachable — %s", exc)

    # PostgreSQL probe
    try:
        import psycopg2
        db_url = os.environ.get("STORAGE_DATABASE_URL", "")
        if db_url:
            conn = psycopg2.connect(db_url, connect_timeout=3)
            conn.close()
            postgres_ok = True
        else:
            logger.warning("Health: STORAGE_DATABASE_URL not set")
    except Exception as exc:
        logger.warning("Health: PostgreSQL unreachable — %s", exc)

    return {
        "status": "ok",
        "service": "pulsegen-admin",
        "redis": "ok" if redis_ok else "unreachable",
        "postgres": "ok" if postgres_ok else "unreachable",
    }
