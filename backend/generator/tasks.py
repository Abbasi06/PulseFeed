from __future__ import annotations

import logging

from celery import Task

from .agent import GeneratorAgent
from .celery_app import app
from .schemas import ExtractedDocument, RawDocument

logger = logging.getLogger(__name__)

# Retry policies
_HARVEST_RETRY = {"max_retries": 3, "default_retry_delay": 60}
_GATEKEEPER_RETRY = {"max_retries": 2, "default_retry_delay": 30}
_EXTRACTOR_RETRY = {"max_retries": 2, "default_retry_delay": 60}
_STORAGE_RETRY = {"max_retries": 5, "default_retry_delay": 10}


@app.task(bind=True, name="generator.tasks.harvest_task", **_HARVEST_RETRY)
def harvest_task(self: Task, source: str, query: str, max_results: int = 20) -> int:
    """Phase 1: Harvest from a data source, fan out to gatekeeper_task."""
    try:
        agent = GeneratorAgent()
        docs = agent.harvest(source, query, max_results)
        for doc in docs:
            gatekeeper_task.delay(doc.model_dump())
        logger.info("harvest_task: queued %d docs from %s", len(docs), source)
        return len(docs)
    except Exception as exc:
        logger.error("harvest_task failed for source=%s: %s", source, exc)
        raise self.retry(exc=exc)


@app.task(bind=True, name="generator.tasks.gatekeeper_task", **_GATEKEEPER_RETRY)
def gatekeeper_task(self: Task, raw_doc_dict: dict) -> None:
    """Phase 2: Classify metadata; if passes, chain to extractor_task."""
    try:
        doc = RawDocument(**raw_doc_dict)
        agent = GeneratorAgent()
        result = agent.gatekeeper(doc)
        if result is None:
            return  # discarded
        extractor_task.delay(raw_doc_dict, result.confidence)
    except Exception as exc:
        logger.error("gatekeeper_task failed for %s: %s", raw_doc_dict.get("url"), exc)
        raise self.retry(exc=exc)


@app.task(bind=True, name="generator.tasks.extractor_task", **_EXTRACTOR_RETRY)
def extractor_task(self: Task, raw_doc_dict: dict, gatekeeper_confidence: float) -> None:
    """Phase 3: Deep extract; if succeeds, chain to storage_router_task."""
    try:
        doc = RawDocument(**raw_doc_dict)
        agent = GeneratorAgent()
        extracted = agent.extract(doc)
        if extracted is None:
            return  # discarded after retries
        storage_router_task.delay(raw_doc_dict, extracted.model_dump(), gatekeeper_confidence)
    except Exception as exc:
        logger.error("extractor_task failed for %s: %s", raw_doc_dict.get("url"), exc)
        raise self.retry(exc=exc)


@app.task(bind=True, name="generator.tasks.storage_router_task", **_STORAGE_RETRY)
def storage_router_task(
    self: Task,
    raw_doc_dict: dict,
    extracted_dict: dict,
    gatekeeper_confidence: float,
) -> dict:
    """Phase 4: Store to SQLite + vector DB. Dead-letters on final failure."""
    try:
        doc = RawDocument(**raw_doc_dict)
        extracted = ExtractedDocument(**extracted_dict)
        agent = GeneratorAgent()
        payload = agent.store(doc, extracted, gatekeeper_confidence)
        return payload.model_dump(mode="json")
    except Exception as exc:
        logger.error("storage_router_task failed for %s: %s", raw_doc_dict.get("url"), exc)
        if self.request.retries >= self.max_retries:
            _dead_letter(raw_doc_dict, extracted_dict, str(exc))
        raise self.retry(exc=exc)


def _dead_letter(raw_doc_dict: dict, extracted_dict: dict, error: str) -> None:
    """Write failed storage payload to Redis dead-letter key for manual replay."""
    import json
    from datetime import datetime, timezone

    try:
        import redis

        r = redis.Redis.from_url(app.conf.broker_url)
        entry = {
            "raw_doc": raw_doc_dict,
            "extracted": extracted_dict,
            "error": error,
            "failed_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        r.lpush("dead_letter_storage", json.dumps(entry))
        logger.error("Payload pushed to dead_letter_storage for manual replay")
    except Exception as redis_exc:
        logger.error("Failed to write dead letter: %s", redis_exc)
