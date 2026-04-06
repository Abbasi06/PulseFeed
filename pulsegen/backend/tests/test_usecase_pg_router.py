"""
Use-case tests for src/storage/pg_router.py — PostgreSQL storage via MCP.

route_to_postgres() is the only public entry point.
All MCP subprocess calls are mocked — no real process spawning.

Covers:
- Happy path: embedding generated + document inserted → StorageConfirmation(success=True)
- Empty or missing embedding → StorageConfirmation(success=False)
- Missing document_id in insert response → StorageConfirmation(success=False)
- MCP client raises MCPError → StorageConfirmation(success=False, error=...)
- MCP client raises generic exception → StorageConfirmation(success=False, error=...)
- published_at=None → None passed to insert args
- published_at with value → ISO-8601 string in insert args
- taxonomy_tags converted to plain strings (not enum members)
- bm25_keywords passed as list (not joined string)
- All StoragePayload fields forwarded to pg_insert_document
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from src.schemas import DataSource, StoragePayload

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_payload(**overrides: object) -> StoragePayload:
    base = {
        "source": DataSource.ARXIV,
        "source_id": "2401.12345",
        "url": "https://arxiv.org/abs/2401.12345",
        "url_hash": "a" * 64,
        "content_hash": "b" * 64,
        "title": "Flash Attention 3: Optimising Transformer Inference",
        "author": "Tri Dao",
        "published_at": datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        "summary": "Sentence one. Sentence two. Sentence three.",
        "bm25_keywords": ["Flash", "Attention", "H100", "CUDA", "BF16"],
        "taxonomy_tags": ["AI Engineering", "GPU Optimization"],
        "image_url": "https://arxiv.org/fig1.png",
        "gatekeeper_confidence": 0.92,
    }
    base.update(overrides)
    return StoragePayload.model_validate(base)


def _mock_mcp_ctx(side_effects: list) -> tuple:
    """
    Returns (patch context manager, mock mcp instance) for MCPClient.
    side_effects: list of return values for each successive mcp.call() invocation.
    """
    mock_mcp = MagicMock()
    mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
    mock_mcp.__exit__ = MagicMock(return_value=False)
    mock_mcp.call.side_effect = side_effects
    return mock_mcp


# ─── Happy path ───────────────────────────────────────────────────────────────


class TestRouteToPostgresHappyPath:
    def test_returns_success_confirmation(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.1] * 768},         # generate_embedding
            {"document_id": "uuid-doc-001"},      # pg_insert_document
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.success is True
        assert result.document_id == "uuid-doc-001"
        assert result.error is None

    def test_calls_generate_embedding_first(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-1"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(_make_payload())

        first_call = mock_mcp.call.call_args_list[0]
        assert first_call.args[0] == "generate_embedding"

    def test_calls_pg_insert_document_second(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-2"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(_make_payload())

        second_call = mock_mcp.call.call_args_list[1]
        assert second_call.args[0] == "pg_insert_document"

    def test_embedding_text_is_summary_plus_keywords(self) -> None:
        """generate_embedding receives summary + space-joined keywords."""
        from src.storage.pg_router import route_to_postgres

        payload = _make_payload()
        expected_text = payload.summary + " " + " ".join(payload.bm25_keywords)

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-3"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(payload)

        embed_args = mock_mcp.call.call_args_list[0]
        assert embed_args.args[1]["text"] == expected_text

    def test_taxonomy_tags_passed_as_strings(self) -> None:
        """Enum members must be converted to plain strings before MCP call."""
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-4"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(_make_payload())

        insert_args = mock_mcp.call.call_args_list[1].args[1]
        taxonomy = insert_args["taxonomy_tags"]
        assert all(isinstance(t, str) for t in taxonomy), (
            f"taxonomy_tags must be plain strings, got: {taxonomy!r}"
        )

    def test_bm25_keywords_passed_as_list(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-5"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(_make_payload())

        insert_args = mock_mcp.call.call_args_list[1].args[1]
        assert isinstance(insert_args["bm25_keywords"], list)

    def test_published_at_serialised_to_iso8601(self) -> None:
        from src.storage.pg_router import route_to_postgres

        dt = datetime(2024, 3, 15, 10, 30, 0, tzinfo=UTC)
        payload = _make_payload(published_at=dt)

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-6"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(payload)

        insert_args = mock_mcp.call.call_args_list[1].args[1]
        published_str = insert_args["published_at"]
        assert published_str == dt.isoformat()

    def test_none_published_at_passed_as_none(self) -> None:
        from src.storage.pg_router import route_to_postgres

        payload = _make_payload(published_at=None)

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-7"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(payload)

        insert_args = mock_mcp.call.call_args_list[1].args[1]
        assert insert_args["published_at"] is None

    def test_all_payload_fields_forwarded_to_insert(self) -> None:
        from src.storage.pg_router import route_to_postgres

        payload = _make_payload()

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-8"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(payload)

        insert_args = mock_mcp.call.call_args_list[1].args[1]
        required_fields = {
            "source", "source_id", "url", "url_hash", "content_hash",
            "title", "author", "published_at", "summary", "bm25_keywords",
            "taxonomy_tags", "image_url", "gatekeeper_confidence",
            "embedding", "pipeline_status",
        }
        for field in required_fields:
            assert field in insert_args, f"Missing field in pg_insert_document args: {field!r}"

    def test_processed_at_is_iso8601_string_in_insert_args(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {"document_id": "doc-9"},
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            route_to_postgres(_make_payload())

        insert_args = mock_mcp.call.call_args_list[1].args[1]
        processed_at_str = insert_args.get("processed_at")
        assert isinstance(processed_at_str, str)
        # Must be parseable
        dt = datetime.fromisoformat(processed_at_str)
        assert dt is not None


# ─── Failure cases ────────────────────────────────────────────────────────────


class TestRouteToPostgresFailures:
    def test_empty_embedding_returns_failure(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": []},  # empty vector
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.success is False
        assert result.error is not None
        assert "empty" in result.error.lower() or "vector" in result.error.lower()

    def test_missing_embedding_key_returns_failure(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {},  # no "embedding" key
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.success is False
        assert result.error is not None

    def test_missing_document_id_returns_failure(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([
            {"embedding": [0.0] * 768},
            {},  # no "document_id"
        ])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.success is False
        assert result.error is not None

    def test_mcp_error_on_embedding_returns_failure(self) -> None:
        from src.storage.mcp_client import MCPError
        from src.storage.pg_router import route_to_postgres

        mock_mcp = MagicMock()
        mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
        mock_mcp.__exit__ = MagicMock(return_value=False)
        mock_mcp.call.side_effect = MCPError("embedding service unavailable")

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.success is False
        assert "embedding service unavailable" in (result.error or "")

    def test_mcp_error_on_insert_returns_failure(self) -> None:
        from src.storage.mcp_client import MCPError
        from src.storage.pg_router import route_to_postgres

        mock_mcp = MagicMock()
        mock_mcp.__enter__ = MagicMock(return_value=mock_mcp)
        mock_mcp.__exit__ = MagicMock(return_value=False)
        mock_mcp.call.side_effect = [
            {"embedding": [0.0] * 768},
            MCPError("unique constraint violation"),
        ]

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.success is False
        assert result.error is not None

    def test_generic_exception_returns_failure_not_raised(self) -> None:
        """Unhandled exceptions must be caught and returned as failure — not propagated."""
        from src.storage.pg_router import route_to_postgres

        mock_mcp = MagicMock()
        mock_mcp.__enter__ = MagicMock(side_effect=OSError("subprocess spawn failed"))
        mock_mcp.__exit__ = MagicMock(return_value=False)

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())  # must not raise

        assert result.success is False
        assert result.error is not None

    def test_failure_confirmation_has_no_document_id(self) -> None:
        from src.storage.pg_router import route_to_postgres

        mock_mcp = _mock_mcp_ctx([{"embedding": []}])

        with patch("src.storage.pg_router.MCPClient", return_value=mock_mcp):
            result = route_to_postgres(_make_payload())

        assert result.document_id is None


# ─── MCP environment ─────────────────────────────────────────────────────────


class TestMcpEnvConfiguration:
    def test_mcp_env_includes_gemini_api_key(self) -> None:
        from src.storage.pg_router import _mcp_env

        env = _mcp_env()
        assert "GEMINI_API_KEY" in env
        assert env["GEMINI_API_KEY"]  # non-empty

    def test_mcp_env_includes_storage_database_url(self) -> None:
        from src.storage.pg_router import _mcp_env

        env = _mcp_env()
        assert "STORAGE_DATABASE_URL" in env
        assert env["STORAGE_DATABASE_URL"]  # non-empty

    def test_mcp_env_is_copy_of_os_environ(self) -> None:
        """_mcp_env must return a copy, not a reference to os.environ."""
        import os

        from src.storage.pg_router import _mcp_env

        env = _mcp_env()
        assert env is not os.environ
