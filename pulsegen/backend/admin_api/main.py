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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)

# CORS: restricted to pulsegen_web (3001) and localhost
_ALLOWED_ORIGINS = [
    "http://localhost:3001",
    "http://localhost:3000",
    "http://localhost",
    *([o.strip() for o in os.environ.get("PULSEGEN_ADMIN_ALLOWED_ORIGIN", "").split(",")]
      if os.environ.get("PULSEGEN_ADMIN_ALLOWED_ORIGIN") else []),
]

app = FastAPI(title="PulseGen Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Import and register routers
from .routes import stats, sources, pipeline, trends, dead_letter

app.include_router(stats.router, prefix="/admin")
app.include_router(sources.router, prefix="/admin")
app.include_router(pipeline.router, prefix="/admin")
app.include_router(trends.router, prefix="/admin")
app.include_router(dead_letter.router, prefix="/admin")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pulsegen-admin"}
