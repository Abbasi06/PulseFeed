"""
Two-Stage Recommender — Live Demo
----------------------------------
Demonstrates the full Retriever + Validator pipeline without requiring
PostgreSQL, Redis, or Celery.

What runs for real (live Gemini API calls):
  - Stage 1 profile embedding  : text-embedding-004 (768-dim vector)
  - Stage 2 RL reward scoring  : gemini-2.5-flash (personalization scores)

What is simulated:
  - pg_hybrid_search result    : 15 hand-crafted CandidateDocuments
    representing a realistic corpus mix (highly relevant → off-topic)

Two scenarios are run back-to-back:
  Scenario A — Cold start   (no interaction history)
  Scenario B — Warm user    (has liked, read, and skipped items)

Usage:
    cd backend
    uv run python -m generator.demo_recommender
"""

from __future__ import annotations

import io
import logging
import sys
import textwrap
import time
from pathlib import Path

# ── force UTF-8 on Windows ────────────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from generator.schemas import (  # noqa: E402
    CandidateDocument,
    FeedCachePayload,
    UserFeedbackHistory,
    UserProfile,
)
from generator.prompts import build_validator_prompt  # noqa: E402
from generator.validator_node import _parse_scores, _to_feed_item, SCORE_THRESHOLD, TOP_N  # noqa: E402

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)

# ─────────────────────────────────────────────────────────────────────────────
# Terminal colours
# ─────────────────────────────────────────────────────────────────────────────

BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
MAGENTA = "\033[95m"
BLUE   = "\033[94m"
DIM    = "\033[2m"
RESET  = "\033[0m"


def hr(char: str = "─", width: int = 72) -> str:
    return DIM + char * width + RESET


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'━' * 72}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'━' * 72}{RESET}")


def subsection(title: str) -> None:
    print(f"\n{hr()}")
    print(f"  {BOLD}{title}{RESET}")
    print(f"{hr()}")


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic candidate corpus  (15 documents, realistic variety)
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES: list[CandidateDocument] = [
    CandidateDocument(
        id=1,
        title="FluxServe: Disaggregated LLM Serving with Speculative Decoding",
        summary=(
            "FluxServe introduces a two-level KV-Cache hierarchy (L1 on-device SRAM / "
            "L2 CXL pool) combined with Medusa-head speculative decoding to achieve "
            "sub-50ms TTFT at p95 under production traffic. GPU memory fragmentation "
            "drops 62% vs baseline TensorRT-LLM; throughput improves 3.4x on A100/H100 "
            "clusters. Integrates with KEDA for Kubernetes-native autoscaling."
        ),
        keywords=["speculative decoding", "KV-cache", "vLLM", "PagedAttention", "KEDA", "CXL"],
        trend_score=0.91,
        matched_trends=["Speculative Decoding", "vLLM", "KEDA"],
        final_score=0.87,
    ),
    CandidateDocument(
        id=2,
        title="LoRA Adapter Hot-Swap in Multi-Tenant LLM Deployments",
        summary=(
            "Describes a zero-downtime LoRA adapter swap mechanism for multi-tenant "
            "serving, leveraging RDMA-backed weight streaming over InfiniBand. "
            "128-GPU cluster benchmarks show < 2ms adapter switch latency. "
            "GPTQ 4-bit quantization of draft models reduces cold-start latency "
            "with no measurable quality regression on MMLU and HumanEval."
        ),
        keywords=["LoRA", "GPTQ", "RDMA", "InfiniBand", "multi-tenant", "quantization"],
        trend_score=0.85,
        matched_trends=["LoRA", "GPTQ"],
        final_score=0.82,
    ),
    CandidateDocument(
        id=3,
        title="Mamba2 State-Space Models: Linear-Time Long-Context Inference",
        summary=(
            "vLLM adds native Mamba2 SSM support, enabling linear-time inference "
            "for long-context tasks and eliminating the quadratic KV-cache growth "
            "bottleneck of transformer architectures. Selective state-space scan "
            "kernels achieve 2.1x throughput on 128k-token sequences vs FlashAttention-2."
        ),
        keywords=["Mamba2", "SSM", "vLLM", "long-context", "FlashAttention", "state-space"],
        trend_score=0.88,
        matched_trends=["Mamba2", "FlashAttention"],
        final_score=0.79,
    ),
    CandidateDocument(
        id=4,
        title="DeepSpeed ZeRO-Infinity: Trillion-Parameter Training on Commodity Hardware",
        summary=(
            "ZeRO-Infinity extends NVMe offloading to optimizer states, making 1T+ "
            "parameter training accessible without NVLink topology. Gradient "
            "checkpointing with selective recomputation guided by activation memory "
            "profiling achieves 38% memory reduction vs naive checkpointing. "
            "Benchmarked on Llama-3.1 405B training recipe."
        ),
        keywords=["ZeRO-Infinity", "NVMe offload", "gradient checkpointing", "DeepSpeed", "FP8"],
        trend_score=0.82,
        matched_trends=["ZeRO-Infinity", "DeepSpeed"],
        final_score=0.76,
    ),
    CandidateDocument(
        id=5,
        title="Mixtral-8x22B: Sparse MoE Routing with FlashAttention-3 Kernels",
        summary=(
            "Mistral AI's technical note details sliding window attention in "
            "Mixtral-8x22B. Sparse Mixture-of-Experts routing combined with "
            "FlashAttention-3 kernels cuts per-token FLOP count by 65% while "
            "maintaining perplexity parity with dense models at 22B activated parameters."
        ),
        keywords=["Mixture-of-Experts", "FlashAttention-3", "sliding window attention", "MoE", "sparse routing"],
        trend_score=0.84,
        matched_trends=["FlashAttention-3", "MoE"],
        final_score=0.74,
    ),
    CandidateDocument(
        id=6,
        title="eBPF-Based Continuous Profiling with Parca at Stripe",
        summary=(
            "Stripe's engineering blog describes replacing sampling profilers with "
            "eBPF-based continuous profiling via Parca. CPU flame graphs are generated "
            "kernel-side with < 1% overhead. Coupled with io_uring async I/O on "
            "bare-metal instances, write-heavy ledger segments bypass the kernel page "
            "cache entirely, improving p99 latency from 12ms to 2.1ms."
        ),
        keywords=["eBPF", "Parca", "io_uring", "flame graphs", "continuous profiling"],
        trend_score=0.77,
        matched_trends=["eBPF", "io_uring"],
        final_score=0.71,
    ),
    CandidateDocument(
        id=7,
        title="FoundationDB-Backed Ledger: From XA to Saga Pattern",
        summary=(
            "Migrating Stripe's ledger from XA two-phase commit to FoundationDB's "
            "ordered KV semantics and saga-pattern compensating transactions. "
            "Idempotent append-only events in a Kafka compacted topic enable full "
            "log replay. Debezium CDC feeds an Apache Iceberg read replica on S3 "
            "queryable via Trino."
        ),
        keywords=["FoundationDB", "Kafka", "MVCC", "Debezium", "Iceberg", "Trino", "saga pattern"],
        trend_score=0.74,
        matched_trends=["FoundationDB", "Debezium"],
        final_score=0.68,
    ),
    CandidateDocument(
        id=8,
        title="KEDA v2.14: HTTP-Triggered Scaling for Serverless Inference",
        summary=(
            "KEDA 2.14 introduces an HTTP add-on scaler that reacts to request-queue "
            "depth rather than CPU metrics, enabling true scale-to-zero for ML inference "
            "workloads. Tested with vLLM serving pods on GKE Autopilot; cold-start "
            "from zero reaches first-token in < 8s with pre-warmed image caching."
        ),
        keywords=["KEDA", "scale-to-zero", "vLLM", "GKE Autopilot", "serverless inference"],
        trend_score=0.79,
        matched_trends=["KEDA"],
        final_score=0.65,
    ),
    CandidateDocument(
        id=9,
        title="OpenTelemetry Collector: Tail-Based Sampling for High-Cardinality Traces",
        summary=(
            "Guide to configuring OTel Collector's tail-based sampling processor for "
            "services generating > 100k spans/sec. Probabilistic + rule-based hybrid "
            "strategy retains all error traces and 1% of success traces, reducing "
            "Jaeger ingestion costs by 82% while preserving full observability for "
            "anomalous requests."
        ),
        keywords=["OpenTelemetry", "tail sampling", "Jaeger", "observability", "OTel Collector"],
        trend_score=0.68,
        matched_trends=["OpenTelemetry"],
        final_score=0.61,
    ),
    CandidateDocument(
        id=10,
        title="pgvector 0.8: HNSW Index Tuning for Sub-Millisecond ANN Search",
        summary=(
            "PostgreSQL pgvector 0.8 introduces configurable HNSW `ef_construction` "
            "and `m` parameters, cutting approximate nearest-neighbour query time to "
            "< 1ms at 99th percentile on 1M 768-dim vectors. Combines with "
            "`pg_trgm` for hybrid BM25 + semantic search without leaving the "
            "Postgres stack."
        ),
        keywords=["pgvector", "HNSW", "ANN", "PostgreSQL", "vector search", "BM25"],
        trend_score=0.72,
        matched_trends=["pgvector", "HNSW"],
        final_score=0.59,
    ),
    CandidateDocument(
        id=11,
        title="React Server Components: Data Fetching Patterns in Next.js 15",
        summary=(
            "Overview of RSC async data fetching in Next.js 15 App Router. Covers "
            "streaming Suspense boundaries, parallel route segments, and avoiding "
            "waterfall fetches with Promise.all. Discusses trade-offs between "
            "client and server component boundaries for interactive dashboards."
        ),
        keywords=["React Server Components", "Next.js", "Suspense", "App Router", "streaming"],
        trend_score=0.55,
        matched_trends=["React Server Components"],
        final_score=0.44,
    ),
    CandidateDocument(
        id=12,
        title="SwiftUI Performance: Reducing View Identity Churn in Large Lists",
        summary=(
            "Analysis of SwiftUI's diffing algorithm and how explicit `id` modifiers "
            "prevent unnecessary view re-creation in lists with 10k+ items. "
            "Instruments profiling shows 40% reduction in commit phase CPU time "
            "when switching from implicit to stable identity."
        ),
        keywords=["SwiftUI", "View identity", "Instruments", "iOS", "performance"],
        trend_score=0.41,
        matched_trends=[],
        final_score=0.36,
    ),
    CandidateDocument(
        id=13,
        title="CSS Anchor Positioning: Replace Popper.js with Native Layout",
        summary=(
            "The CSS Anchor Positioning API lands in Chrome 125, enabling tooltips "
            "and popover positioning relative to arbitrary anchors without JavaScript. "
            "Reduces bundle size by eliminating Popper.js. Fallback strategy using "
            "`@supports` targets Safari and Firefox until baseline support arrives."
        ),
        keywords=["CSS Anchor Positioning", "Popper.js", "Chrome 125", "popover", "CSS"],
        trend_score=0.33,
        matched_trends=[],
        final_score=0.28,
    ),
    CandidateDocument(
        id=14,
        title="WordPress Block Theme Development: Full-Site Editing Patterns",
        summary=(
            "Beginner's walkthrough for creating custom block themes using the "
            "WordPress Site Editor. Covers `theme.json` global styles, template "
            "hierarchy, and block patterns registration. Compares performance "
            "against classic PHP themes using Core Web Vitals metrics."
        ),
        keywords=["WordPress", "block theme", "Site Editor", "PHP", "theme.json"],
        trend_score=0.21,
        matched_trends=[],
        final_score=0.19,
    ),
    CandidateDocument(
        id=15,
        title="Excel XLOOKUP vs VLOOKUP: Which Function Should You Use?",
        summary=(
            "Comparison guide for XLOOKUP and VLOOKUP in Microsoft Excel. Explains "
            "how XLOOKUP handles left-column lookups, wildcard matching, and multiple "
            "return arrays. Includes a downloadable template for common HR reporting "
            "scenarios."
        ),
        keywords=["Excel", "XLOOKUP", "VLOOKUP", "spreadsheet", "Microsoft Office"],
        trend_score=0.05,
        matched_trends=[],
        final_score=0.08,
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# User profiles
# ─────────────────────────────────────────────────────────────────────────────

PROFILE = UserProfile(
    user_id=42,
    field="Machine Learning Engineering",
    subfields=[
        "LLM Serving Systems",
        "Distributed Training",
        "MLOps",
        "Vector Databases",
        "Inference Optimization",
    ],
    recent_search_history=["vLLM speculative decoding", "LoRA fine-tuning", "KV-cache eviction"],
)

FEEDBACK_COLD = UserFeedbackHistory(
    user_id=42,
    liked=[],
    clicked=[],
    ignored=[],
    read_complete=[],
)

FEEDBACK_WARM = UserFeedbackHistory(
    user_id=42,
    liked=[1, 3],           # liked FluxServe and Mamba2
    clicked=[2, 4, 6],      # clicked LoRA, DeepSpeed, eBPF
    read_complete=[1, 5],   # read to end: FluxServe, Mixtral MoE
    ignored=[11, 12, 13],   # skipped: React, SwiftUI, CSS
)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Profile embedding (real Gemini call)
# ─────────────────────────────────────────────────────────────────────────────

def run_stage1(profile: UserProfile) -> list[float]:
    section("STAGE 1 — HYBRID RETRIEVER  (RetrieverAgent)")

    print(f"\n  {BOLD}User Profile{RESET}")
    print(f"  {'user_id':<24} {CYAN}{profile.user_id}{RESET}")
    print(f"  {'field':<24} {CYAN}{profile.field}{RESET}")
    print(f"  {'subfields':<24} {CYAN}{', '.join(profile.subfields)}{RESET}")
    print(f"  {'search history':<24} {DIM}{', '.join(profile.recent_search_history)}{RESET}")

    subsection("Step A — Build BM25 keyword query")
    kw_query = profile.field + " " + " ".join(profile.subfields[:5])
    print(f"\n  Keyword query : {YELLOW}\"{kw_query}\"{RESET}")

    subsection("Step B — Embed profile with text-embedding-004  (live API call)")
    import os
    from google import genai
    from google.genai import types as gtypes

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(f"  {RED}GEMINI_API_KEY not set — cannot embed profile.{RESET}")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    profile_text = (
        f"{profile.field}. "
        f"{' '.join(profile.subfields)}. "
        f"{' '.join(profile.recent_search_history[:5])}"
    )
    print(f"\n  Input text  : \"{DIM}{profile_text[:80]}...{RESET}\"")

    t0 = time.perf_counter()
    response = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=profile_text,
        config=gtypes.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    elapsed = (time.perf_counter() - t0) * 1000
    embeddings = response.embeddings or []
    embedding: list[float] = list(embeddings[0].values or [])

    print(f"  Dimensions  : {GREEN}{len(embedding)}{RESET}")
    print(f"  Latency     : {GREEN}{elapsed:.0f} ms{RESET}")
    preview = "  [" + ", ".join(f"{v:.4f}" for v in embedding[:6]) + ", ...]"
    print(f"  Vector head : {DIM}{preview}{RESET}")

    subsection("Step C — pg_hybrid_search result  (simulated — no PG required)")
    print("\n  Would execute SQL:")
    print(f"  {DIM}SELECT id, title, summary, keywords, trend_score, matched_trends,{RESET}")
    print(f"  {DIM}       0.4*(1 - embedding<=>$1) + 0.3*ts_rank(...) + 0.3*trend_score AS final_score{RESET}")
    print(f"  {DIM}FROM documents{RESET}")
    print(f"  {DIM}ORDER BY final_score DESC LIMIT 50;{RESET}")
    print(f"\n  Returning {CYAN}{len(CANDIDATES)} synthetic candidates{RESET} that mirror realistic PG output.\n")

    print(f"  {'#':<4} {'ID':<5} {'final_score':<13} Title")
    print(f"  {DIM}{'─'*65}{RESET}")
    for i, c in enumerate(CANDIDATES, 1):
        bar_len = int(c.final_score * 20)
        bar = GREEN + "█" * bar_len + DIM + "░" * (20 - bar_len) + RESET
        title_short = c.title[:45] + ("…" if len(c.title) > 45 else "")
        score_color = GREEN if c.final_score >= 0.6 else (YELLOW if c.final_score >= 0.35 else RED)
        print(f"  {i:<4} {c.id:<5} {score_color}{c.final_score:.3f}{RESET}  {bar}  {DIM}{title_short}{RESET}")

    return embedding


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Validator Node (real Gemini call)
# ─────────────────────────────────────────────────────────────────────────────

def run_stage2(
    label: str,
    feedback: UserFeedbackHistory,
    scenario_note: str,
) -> FeedCachePayload:
    section(f"STAGE 2 — RL VALIDATOR NODE  ({label})")

    print(f"\n  {BOLD}Feedback History{RESET}")
    print(f"  {'liked':<20} {GREEN}{feedback.liked or '(none)'}{RESET}")
    print(f"  {'clicked':<20} {CYAN}{feedback.clicked or '(none)'}{RESET}")
    print(f"  {'read_complete':<20} {YELLOW}{feedback.read_complete or '(none)'}{RESET}")
    print(f"  {'ignored/skipped':<20} {RED}{feedback.ignored or '(none)'}{RESET}")
    print(f"\n  {DIM}{scenario_note}{RESET}")

    subsection("Step A — Build Validator prompt  (VALIDATOR_PROMPT_TEMPLATE)")
    candidates_dicts = [c.model_dump() for c in CANDIDATES]
    prompt = build_validator_prompt(candidates_dicts, feedback)
    print(f"\n  Prompt length : {len(prompt):,} chars  |  {len(CANDIDATES)} candidate documents")
    preview_lines = prompt.split("\n")[:6]
    for line in preview_lines:
        print(f"  {DIM}{line}{RESET}")
    print(f"  {DIM}... (truncated){RESET}")

    subsection("Step B — gemini-2.5-flash reward scoring  (live API call)")
    import os
    from google import genai
    from google.genai import types as gtypes

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    config = gtypes.GenerateContentConfig(response_mime_type="application/json")

    t0 = time.perf_counter()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    elapsed = (time.perf_counter() - t0) * 1000

    raw_text = response.text or ""
    score_lookup = _parse_scores(raw_text)

    print(f"\n  Latency       : {GREEN}{elapsed:.0f} ms{RESET}")
    print(f"  Scores parsed : {GREEN}{len(score_lookup)}/{len(CANDIDATES)}{RESET}")

    subsection("Step C — Scoring table  (all 15 candidates)")
    feed_items = [_to_feed_item(c, score_lookup) for c in CANDIDATES]

    print(f"\n  {'ID':<5} {'P-Score':<10} {'HybridScore':<13} {'Pass?':<7} Title")
    print(f"  {DIM}{'─'*72}{RESET}")
    for item, cand in zip(feed_items, CANDIDATES):
        passes = item.personalization_score >= SCORE_THRESHOLD
        pass_icon = f"{GREEN}✓{RESET}" if passes else f"{RED}✗{RESET}"
        score_color = GREEN if item.personalization_score >= 0.65 else (YELLOW if item.personalization_score >= 0.4 else RED)
        title_short = item.title[:40] + ("…" if len(item.title) > 40 else "")
        print(
            f"  {item.id:<5} {score_color}{item.personalization_score:.3f}{RESET}     "
            f"{DIM}{cand.final_score:.3f}{RESET}        {pass_icon}      {DIM}{title_short}{RESET}"
        )

    subsection(f"Step D — Final feed  (threshold >= {SCORE_THRESHOLD}, top {TOP_N})")
    filtered = [i for i in feed_items if i.personalization_score >= SCORE_THRESHOLD]
    filtered.sort(key=lambda x: x.personalization_score, reverse=True)
    top = filtered[:TOP_N]

    print(f"\n  {GREEN}{len(filtered)}{RESET} items passed threshold  →  top {CYAN}{len(top)}{RESET} selected\n")
    for rank, item in enumerate(top, 1):
        bar_len = int(item.personalization_score * 30)
        bar = CYAN + "█" * bar_len + DIM + "░" * (30 - bar_len) + RESET
        print(f"  {BOLD}#{rank:<3}{RESET} {bar}  {MAGENTA}{item.personalization_score:.3f}{RESET}")
        print(f"       {BOLD}{item.title}{RESET}")
        wrapped = textwrap.fill(item.summary, width=62, initial_indent="       ", subsequent_indent="       ")
        print(f"{DIM}{wrapped}{RESET}")
        if item.tags:
            tags_str = "  ".join(f"{CYAN}[{t}]{RESET}" for t in item.tags[:4])
            print(f"       Tags: {tags_str}")
        print()

    from datetime import datetime, timezone
    payload = FeedCachePayload(
        user_id=PROFILE.user_id,
        items=top,
        generated_at=datetime.now(tz=timezone.utc),
    )

    print(f"  {DIM}Redis key  : pulsefeed:feed:v2:{PROFILE.user_id}  (TTL 6h){RESET}")
    print(f"  {DIM}Payload    : {len(top)} items, generated_at={payload.generated_at.isoformat()}{RESET}")
    print(f"  {DIM}(cache_feed() skipped in demo — no Redis required){RESET}")

    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{BOLD}{CYAN}{'═' * 72}{RESET}")
    print(f"{BOLD}{CYAN}  PulseBoard — Two-Stage Recommender  LIVE DEMO{RESET}")
    print(f"{BOLD}{CYAN}  user_id=42  |  field=Machine Learning Engineering{RESET}")
    print(f"{BOLD}{CYAN}{'═' * 72}{RESET}")

    # Stage 1: embed profile + show retrieval simulation (shared across both scenarios)
    run_stage1(PROFILE)

    # Stage 2A: cold start
    cold_payload = run_stage2(
        label="Scenario A — Cold Start",
        feedback=FEEDBACK_COLD,
        scenario_note=(
            "No prior interactions. Gemini should rank purely on topical diversity "
            "and trend_score, favouring LLM / ML systems content for this profile."
        ),
    )

    # Stage 2B: warm user
    warm_payload = run_stage2(
        label="Scenario B — Warm User",
        feedback=FEEDBACK_WARM,
        scenario_note=(
            "User has liked FluxServe (id=1) and Mamba2 (id=3), read Mixtral MoE (id=5) "
            "to completion, and skipped React/SwiftUI/CSS (ids 11-13). "
            "Expect LLM-serving docs boosted and frontend items further penalised."
        ),
    )

    # ── Delta report ──────────────────────────────────────────────────────────
    section("DELTA REPORT  — Cold Start vs Warm User")
    cold_ids = {item.id: item.personalization_score for item in cold_payload.items}
    warm_ids = {item.id: item.personalization_score for item in warm_payload.items}
    all_ids = sorted(cold_ids.keys() | warm_ids.keys())

    print(f"\n  {'ID':<5} {'Title':<42} {'Cold':>7}  {'Warm':>7}  {'Delta':>7}")
    print(f"  {DIM}{'─'*72}{RESET}")
    for doc_id in all_ids:
        cand = next((c for c in CANDIDATES if c.id == doc_id), None)
        title = (cand.title[:38] + "…") if cand and len(cand.title) > 38 else (cand.title if cand else "?")
        cold_s = cold_ids.get(doc_id, 0.0)
        warm_s = warm_ids.get(doc_id, 0.0)
        delta = warm_s - cold_s
        delta_str = f"+{delta:.3f}" if delta > 0 else f"{delta:.3f}"
        delta_color = GREEN if delta > 0.05 else (RED if delta < -0.05 else DIM)
        print(
            f"  {doc_id:<5} {DIM}{title:<42}{RESET} "
            f"{cold_s:>7.3f}  {warm_s:>7.3f}  {delta_color}{delta_str:>7}{RESET}"
        )

    print(f"\n{hr()}")
    print(f"  {BOLD}Summary{RESET}")
    print(f"  Stage 1 candidate pool : {len(CANDIDATES)} documents")
    print(f"  Stage 2 threshold      : {SCORE_THRESHOLD}")
    print(f"  Cold-start feed size   : {GREEN}{len(cold_payload.items)}{RESET}")
    print(f"  Warm-user feed size    : {GREEN}{len(warm_payload.items)}{RESET}")
    print(f"{hr()}\n")


if __name__ == "__main__":
    main()
