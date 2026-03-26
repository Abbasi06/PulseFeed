from __future__ import annotations

from .schemas import TAXONOMY_TAGS

GATEKEEPER_PROMPT_TEMPLATE = """\
Analyze this document metadata and determine if it is a highly technical, \
high-signal engineering document suitable for a professional tech knowledge feed.

Title: {title}
Author: {author}
Source: {source}
Excerpt (first 500 chars): {excerpt}

Output strictly JSON with no markdown fences:
{{"is_high_signal": <boolean>, "confidence": <float between 0.0 and 1.0>}}
"""

EXTRACTOR_PROMPT_TEMPLATE = """\
Act as a Principal Engineer. Distill the following document for a personalized \
technical knowledge feed.

Output strictly JSON with no markdown fences and exactly these keys:
- summary: A dense, 3-sentence technical summary covering what, why, and impact.
- bm25_keywords: An array of 5 to 10 highly specific technical terms or frameworks \
  (e.g. "vLLM", "KEDA", "eBPF"). No generic words.
- taxonomy_tags: An array of 1 to 3 tags chosen ONLY from this exact list — \
  do not invent new tags: {taxonomy_list}
- image_url: The URL of the primary architectural diagram or header image, \
  or empty string "" if none.

Document:
{body}
"""


def build_gatekeeper_prompt(
    title: str, author: str, source: str, body: str
) -> str:
    return GATEKEEPER_PROMPT_TEMPLATE.format(
        title=title,
        author=author,
        source=source,
        excerpt=body[:500],
    )


def build_extractor_prompt(body: str) -> str:
    return EXTRACTOR_PROMPT_TEMPLATE.format(
        taxonomy_list=sorted(TAXONOMY_TAGS),
        body=body[:8000],  # cap to avoid token overflow
    )


# ---------------------------------------------------------------------------
# Trend Analyst prompt
# ---------------------------------------------------------------------------

_ALLOWED_CATEGORIES = ["Hardware", "Architecture", "Methodology", "Framework", "Model"]

TREND_ANALYST_PROMPT_TEMPLATE = """\
You are a Senior Technical Trend Analyst. Process the text below from a \
cutting-edge developer platform, research paper, or technical newsletter.

EXTRACTION RULES:
1. Be hyper-specific: extract exact model names, mathematical techniques, or \
   architectural frameworks (e.g. "Speculative Decoding", "vLLM", "Flash Attention", \
   "LoRA", "KEDA", "eBPF").
2. Ignore the generic: do NOT extract broad, established terms such as \
   "Artificial Intelligence", "Machine Learning", "Python", "Database", \
   "Algorithm", or "Cloud". Only high-signal, modern terminology.
3. Classify each term into exactly one category from this list: {categories}.

Output ONLY valid JSON — no markdown fences, no commentary:
{{
  "extracted_trends": [
    {{
      "term": "<exact buzzword>",
      "category": "<one of {categories}>",
      "context": "<one sentence explaining how it was used in the text>"
    }}
  ]
}}

Source text:
{text}
"""


def build_trend_analyst_prompt(text: str) -> str:
    return TREND_ANALYST_PROMPT_TEMPLATE.format(
        categories=_ALLOWED_CATEGORIES,
        text=text[:12000],  # generous cap — trend analysis benefits from full context
    )


# ---------------------------------------------------------------------------
# Validator Node (RL Reward Model) prompt
# ---------------------------------------------------------------------------

VALIDATOR_PROMPT_TEMPLATE = """\
You are the Recommendation Validator Node acting as a zero-shot Reward Model.
Score each candidate document for a specific user based on their interaction history.

User Feedback History:
- Liked document IDs       : {liked}
- Clicked document IDs     : {clicked}
- Read-to-completion IDs   : {read_complete}
- Ignored/skipped IDs      : {ignored}

SCORING RULES:
1. For each document, output a `personalization_score` between 0.0 and 1.0.
2. Increase the score if the document's keywords/topics overlap with liked or
   read_complete items.
3. Decrease the score if the document shares traits with consistently ignored
   items, or if it duplicates content already in high-scoring positions.
4. If feedback history is empty, score based purely on topical diversity and
   trend_score (higher trend_score → higher base relevance).
5. Aim for diversity — do not give 50 documents about the same narrow topic
   all high scores.

Output ONLY a JSON array — no markdown, no explanation:
[
  {{"id": <document_id>, "personalization_score": <float 0.0-1.0>}},
  ...
]

Candidate Documents:
{candidates_json}
"""


def build_validator_prompt(
    candidates: list[dict],
    feedback: object,
) -> str:
    """Build the validator prompt from candidates list and feedback history."""
    import json as _json
    slim = [
        {
            "id":             c["id"],
            "title":          c["title"],
            "summary":        c["summary"][:300],
            "keywords":       c["keywords"][:8],
            "trend_score":    c["trend_score"],
            "matched_trends": c["matched_trends"][:5],
        }
        for c in candidates
    ]
    return VALIDATOR_PROMPT_TEMPLATE.format(
        liked=getattr(feedback, "liked", []),
        clicked=getattr(feedback, "clicked", []),
        read_complete=getattr(feedback, "read_complete", []),
        ignored=getattr(feedback, "ignored", []),
        candidates_json=_json.dumps(slim, indent=2),
    )
