"""
Prompt injection sanitizer for LLM-bound user inputs.

Strips known injection patterns, model-specific control tokens, null bytes,
and excessive whitespace from strings before they reach Gemini or the
vector-DB query layer.

Design: strip-only, never raise.  Suspicious content is replaced with a
space and a WARNING is emitted (field name only — never the raw value).
"""
import logging
import re

logger = logging.getLogger(__name__)

# Instruction-override attempts ------------------------------------------------
# Uses (?:...\s+){0,3} to handle multi-qualifier phrases like
# "ignore all previous instructions" (two qualifiers before "instructions").
_OVERRIDE_RE = re.compile(
    r"(?i)"
    r"(ignore\s+(?:(?:all|previous|prior|above)\s+){0,3}instructions?)"
    r"|(disregard\s+(?:(?:all|previous|prior)\s+){0,3}instructions?)"
    r"|(forget\s+(?:(?:all|previous|prior|above)\s+){0,3}instructions?)"
    r"|(override\s+(?:(?:all|previous|prior)\s+){0,3}instructions?)"
    r"|(repeat\s+(your\s+)?(system\s+)?prompt)"
    r"|(output\s+(your\s+)?(system\s+)?prompt)"
    r"|(print\s+(your\s+)?(system\s+)?prompt)",
)

# Role/context injection at line start (MULTILINE so ^ matches each line) ------
_ROLE_PREFIX_RE = re.compile(
    r"(?im)^\s*(system|assistant|user|human)\s*:",
)

# LLM-family special tokens ----------------------------------------------------
_SPECIAL_TOKEN_RE = re.compile(
    r"(<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>)"
    r"|(\[INST\]|\[\/INST\]|<<SYS>>|<\/SYS>>|<\/s>(?!\w))"
    r"|(###\s*(Instruction|Response|Human|Assistant)\s*:)",
    re.IGNORECASE,
)

# Null bytes and non-printable C0 control characters (keep \t and \n) ----------
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Collapse 3+ consecutive newlines to 2 ----------------------------------------
_EXCESS_NEWLINES_RE = re.compile(r"\n{3,}")


def sanitize_llm_input(value: str, field_name: str = "field") -> str:
    """
    Return *value* with injection patterns and control characters removed.

    Never raises.  If content was modified, a WARNING is logged with the
    *field_name* only (the raw value is never included in the log line).
    """
    cleaned = _CONTROL_RE.sub("", value)
    cleaned = _ROLE_PREFIX_RE.sub(" ", cleaned)
    cleaned = _OVERRIDE_RE.sub(" ", cleaned)
    cleaned = _SPECIAL_TOKEN_RE.sub(" ", cleaned)
    cleaned = _EXCESS_NEWLINES_RE.sub("\n\n", cleaned)
    cleaned = cleaned.strip()

    if cleaned != value.strip():
        logger.warning(
            "Prompt injection pattern detected and stripped in field '%s'",
            field_name,
        )

    return cleaned
