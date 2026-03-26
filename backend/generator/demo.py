"""
Generator + Trend Analyst — Live Demo
--------------------------------------
Runs the full Inference Cascade and Trend Analyst sequentially
(no Celery/Redis required).  Needs GEMINI_API_KEY in the environment.

Usage:
    cd backend
    uv run python -m generator.demo
"""

from __future__ import annotations

import io
import logging
import sys
import textwrap
from pathlib import Path

# ── force UTF-8 output on Windows ────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── allow running from backend/ without installing the package ────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from generator.agent import GeneratorAgent  # noqa: E402
from generator.schemas import DataSource, RawDocument  # noqa: E402
from generator.trend_analyst import TrendAnalystAgent  # noqa: E402

logging.basicConfig(
    level=logging.WARNING,          # suppress noisy debug from httpx / chromadb
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)

# ─────────────────────────────────────────────────────────────────────────────
# Sample technical text (realistic ArXiv-style abstract + blog excerpt)
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_TEXTS = [
    {
        "label": "LLM Inference Paper",
        "text": """\
We present FluxServe, a novel serving system for large language models that
combines Speculative Decoding with a disaggregated prefill-decode architecture
to achieve sub-50ms time-to-first-token at 95th percentile under production
traffic. FluxServe introduces a two-level KV-Cache hierarchy: an L1 on-device
SRAM cache backed by an L2 disaggregated KV pool stored on CXL-attached
memory. By co-designing the draft model selection with Medusa heads and
integrating continuous batching via vLLM's PagedAttention, we reduce
GPU-memory fragmentation by 62%. Evaluation on A100 and H100 clusters
demonstrates 3.4x throughput improvement over baseline TensorRT-LLM deployments
at equivalent quality as measured by ROUGE-L and BERTScore metrics. The system
exposes a compatibility layer with the OpenAI-compatible API surface and
integrates with KEDA for Kubernetes-native autoscaling based on queue-depth
signals. We further demonstrate that applying GPTQ 4-bit quantization to the
draft model reduces cold-start latency without measurable quality regression
on the MMLU and HumanEval benchmarks. Our LoRA adapter hot-swap mechanism
enables zero-downtime multi-tenant deployments across 128-GPU clusters using
RDMA-backed weight streaming over InfiniBand fabrics.
""",
    },
    {
        "label": "Database / Systems Blog Post",
        "text": """\
At Stripe, we recently migrated our ledger system from a homegrown two-phase
commit protocol to a deterministic execution engine built on FoundationDB's
ordered key-value semantics. The core insight is that by encoding all account
mutations as idempotent, append-only events in a Kafka compacted topic, we can
replay the entire transaction log to reconstruct balance state without
distributed locks. We use Raft consensus for our control plane metadata while
delegating data-plane replication to FoundationDB's multi-version concurrency
control (MVCC). For analytical queries we maintain a read replica in Apache
Iceberg format on S3, with incremental CDC captured via Debezium and materialised
into Parquet files queryable through Trino. The hot path latency improved from
p99 12ms to p99 2.1ms after eliminating the XA transaction coordinator and
replacing it with saga-pattern compensating transactions. We run this stack on
bare-metal instances with io_uring for async I/O, bypassing the kernel's page
cache entirely for write-heavy ledger segments, and profile CPU flame graphs
using eBPF-based continuous profiling via Parca.
""",
    },
    {
        "label": "ML Systems Newsletter Snippet",
        "text": """\
This week's highlights from the MLSys community: Meta released the training
recipe for Llama-3.1 405B, detailing their use of FP8 mixed-precision training
on 16,000 H100 GPUs interconnected with 400Gbps RoCEv2. The gradient
checkpointing strategy uses selective recomputation guided by activation memory
profiling, achieving 38% memory reduction vs naive checkpointing. Mistral AI
published a technical note on sliding window attention as used in Mixtral-8x22B,
showing that sparse Mixture-of-Experts routing combined with FlashAttention-3
kernels cuts per-token FLOP count by 65% while maintaining perplexity parity
with dense models. Separately, the vLLM team merged support for Mamba2
state-space models, enabling linear-time inference for long-context tasks
without the quadratic KV-cache growth that limits transformer architectures.
The DeepSpeed ZeRO-Infinity update now supports NVMe offloading of optimizer
states for trillion-parameter models, making 1T+ parameter training accessible
on commodity server hardware without NVLink topology.
""",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
RESET  = "\033[0m"

CATEGORY_COLORS = {
    "Hardware":      "\033[95m",   # magenta
    "Architecture":  "\033[94m",   # blue
    "Methodology":   "\033[93m",   # yellow
    "Framework":     "\033[92m",   # green
    "Model":         "\033[96m",   # cyan
}


def hr(char: str = "─", width: int = 70) -> str:
    return DIM + char * width + RESET


def print_trend_results(result: object) -> None:
    from generator.schemas import TrendAnalysisResult
    assert isinstance(result, TrendAnalysisResult)
    if not result.extracted_trends:
        print(f"  {YELLOW}No trends extracted.{RESET}")
        return
    for t in result.extracted_trends:
        color = CATEGORY_COLORS.get(t.category.value, RESET)
        tag = f"{color}[{t.category.value}]{RESET}"
        print(f"  {BOLD}{t.term:<35}{RESET} {tag}")
        wrapped = textwrap.fill(t.context, width=60, initial_indent="    ↳ ", subsequent_indent="      ")
        print(f"{DIM}{wrapped}{RESET}")


def print_phase1_demo() -> None:
    """Show the heuristic bouncer rejecting and accepting documents."""
    print(f"\n{BOLD}{CYAN}━━  PHASE 1 — HEURISTIC BOUNCER DEMO  ━━{RESET}\n")

    cases = [
        {
            "label": "✗  Too short  (word_count < 300)",
            "data":  {"title": "Deep Dive into eBPF Observability", "url": "https://example.com/a",
                      "body": "Short body. " * 20, "source": "rss"},
        },
        {
            "label": "✗  Spam title  (regex: 'Top 10')",
            "data":  {"title": "Top 10 AI Tools You Must Use in 2025",
                      "url": "https://example.com/b",
                      "body": "legitimate " * 310,
                      "source": "rss"},
        },
        {
            "label": "✓  Passes all filters",
            "data":  {"title": "KV-Cache Disaggregation in Production LLM Serving",
                      "url": "https://example.com/c",
                      "body": ("We present a novel approach to KV-Cache management "
                               "using CXL-attached memory pools. " * 40),
                      "source": "arxiv"},
        },
    ]

    for case in cases:
        try:
            doc = RawDocument(**case["data"])  # type: ignore[arg-type]
            print(f"  {GREEN}{case['label']}{RESET}")
            print(f"    → word_count={len(doc.body.split())}  hash={doc.content_hash[:12]}…\n")
        except ValueError as exc:
            print(f"  {RED}{case['label']}{RESET}")
            print(f"    {DIM}→ {exc}{RESET}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────


def run_trend_analyst_demo() -> None:
    print(f"\n{BOLD}{CYAN}{'━'*70}{RESET}")
    print(f"{BOLD}{CYAN}  TREND ANALYST AGENT — LIVE EXTRACTION{RESET}")
    print(f"{BOLD}{CYAN}{'━'*70}{RESET}")

    agent = TrendAnalystAgent()

    for sample in SAMPLE_TEXTS:
        print(f"\n{hr()}")
        print(f"{BOLD}  Source: {sample['label']}{RESET}")
        print(hr())
        result = agent.analyze(sample["text"])
        print_trend_results(result)

    print(f"\n{hr()}\n")


def run_cascade_demo() -> None:
    """Run Phases 2 + 3 directly (no Celery, no MCP) on one sample document."""
    print(f"\n{BOLD}{CYAN}{'━'*70}{RESET}")
    print(f"{BOLD}{CYAN}  INFERENCE CASCADE — PHASE 2 + 3 (direct, no Celery){RESET}")
    print(f"{BOLD}{CYAN}{'━'*70}{RESET}\n")

    # Build a synthetic RawDocument from the LLM inference sample
    body = SAMPLE_TEXTS[0]["text"] * 3   # repeat to exceed 300-word minimum comfortably
    doc = RawDocument(
        title="FluxServe: Disaggregated LLM Serving with Speculative Decoding",
        url="https://arxiv.org/abs/2501.99999",
        body=body,
        author="Demo Author",
        published_at="2025-01-15",
        source=DataSource.ARXIV,
    )

    print(f"  {BOLD}Document:{RESET} {doc.title}")
    print(f"  {DIM}word_count={len(doc.body.split())}  hash={doc.content_hash[:16]}…{RESET}\n")

    agent = GeneratorAgent()

    # ── Phase 2: Gatekeeper ───────────────────────────────────────────────────
    print(f"{BOLD}  ▶ Phase 2 — Metadata Gatekeeper{RESET}  {DIM}(gemini-2.5-flash-lite){RESET}")
    gatekeeper_result = agent.gatekeeper(doc)
    if gatekeeper_result is None:
        print(f"  {RED}  ✗ Rejected by gatekeeper — stopping demo here.{RESET}\n")
        return
    color = GREEN if gatekeeper_result.passes else RED
    print(f"  {color}  is_high_signal = {gatekeeper_result.is_high_signal}{RESET}")
    print(f"  {color}  confidence     = {gatekeeper_result.confidence:.2f}{RESET}")
    print(f"  {color}  passes         = {gatekeeper_result.passes}{RESET}\n")

    # ── Phase 3: Deep Extractor ───────────────────────────────────────────────
    print(f"{BOLD}  ▶ Phase 3 — Deep Extractor{RESET}  {DIM}(gemini-2.5-flash){RESET}")
    extracted = agent.extract(doc)
    if extracted is None:
        print(f"  {RED}  ✗ Extractor failed — see logs.{RESET}\n")
        return

    print(f"\n  {BOLD}Summary:{RESET}")
    for line in textwrap.wrap(extracted.summary, width=66):
        print(f"    {line}")

    print(f"\n  {BOLD}BM25 Keywords:{RESET}")
    for kw in extracted.bm25_keywords:
        print(f"    {CYAN}• {kw}{RESET}")

    print(f"\n  {BOLD}Taxonomy Tags:{RESET}")
    for tag in extracted.taxonomy_tags:
        print(f"    {GREEN}▸ {tag}{RESET}")

    if extracted.image_url:
        print(f"\n  {BOLD}Image URL:{RESET}  {DIM}{extracted.image_url}{RESET}")

    print()


def main() -> None:
    print_phase1_demo()
    run_trend_analyst_demo()
    run_cascade_demo()


if __name__ == "__main__":
    main()
