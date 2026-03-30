"""
PulseGen — Generator Service
-----------------------------
Standalone FastAPI application (port 8001) that harvests content for the
entire application.  Completely separate from the PulseFeed service.

Startup
-------
    cd backend
    uv run uvicorn generator_service.main:app --port 8001 --reload

Environment
-----------
    GEMINI_API_KEY        required
    GENERATOR_DB_PATH     optional — absolute path to generator.db
                          Defaults to backend/generator.db relative to this
                          file.  Both PulseGen and PulseFeed must use the
                          same path.
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from project root (three levels up from generator_service/)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from generator.db import init_db  # noqa: E402
from generator.status_store import AGENT_STATUS  # noqa: E402
from generator.trend_scheduler import run_trend_job  # noqa: E402
from generator_service.swarm import run_swarm_job  # noqa: E402
from routes import generator_obs  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialise generator.db tables (safe to call multiple times)
    init_db()

    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY is not set — harvesting will fail")

    scheduler = BackgroundScheduler(job_defaults={"misfire_grace_time": 60})
    now = datetime.now(tz=timezone.utc)

    # Swarm runs every 5 minutes — fires immediately on startup
    scheduler.add_job(
        run_swarm_job,
        "interval",
        minutes=5,
        id="swarm",
        kwargs={"scheduler": scheduler, "target_docs_per_topic": 5},
        max_instances=1,
        next_run_time=now,
    )

    # Trend analyst runs every 15 minutes — fires immediately on startup
    # (gracefully skips if generator.db has no documents yet)
    scheduler.add_job(
        run_trend_job,
        "interval",
        minutes=15,
        id="trend_analyst",
        kwargs={"scheduler": scheduler},
        max_instances=1,
        next_run_time=now,
    )

    scheduler.start()

    # Seed next_run_at in status store
    for job_id, key in [("swarm", "generator"), ("trend_analyst", "trend_analyst")]:
        job = scheduler.get_job(job_id)
        if job and getattr(job, "next_run_time", None):
            AGENT_STATUS[key]["next_run_at"] = job.next_run_time.isoformat()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="PulseGen API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Re-use the existing generator observer router — all /generator/* endpoints
app.include_router(generator_obs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "pulsegen"}
