"""
In-memory status store for background agents.
Both inline_pipeline and trend_scheduler import and mutate AGENT_STATUS.
Thread-safe for single-writer / multi-reader via the GIL.
"""
from __future__ import annotations

from typing import Any

AGENT_STATUS: dict[str, dict[str, Any]] = {
    "generator": {
        "state": "idle",          # idle | running | success | error
        "phase": None,            # 1-4 when running
        "phase_label": None,      # "Harvest" | "Gatekeeper" | "Extractor" | "Storage"
        "started_at": None,
        "finished_at": None,
        "last_run_at": None,
        "docs_harvested": 0,
        "docs_passed_gate": 0,
        "docs_extracted": 0,
        "docs_stored": 0,
        "docs_skipped": 0,
        "error_message": None,
        "next_run_at": None,
    },
    "trend_analyst": {
        "state": "idle",
        "started_at": None,
        "finished_at": None,
        "last_run_at": None,
        "docs_analyzed": 0,
        "trends_found": 0,
        "last_run_id": None,
        "error_message": None,
        "next_run_at": None,
    },
}
