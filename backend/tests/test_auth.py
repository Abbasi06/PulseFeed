import pytest
from fastapi import HTTPException

from auth import _decode_token, create_access_token, get_current_user_id


def test_create_and_decode_token() -> None:
    token = create_access_token(42)
    assert isinstance(token, str)
    assert _decode_token(token) == 42


def test_different_user_ids_produce_different_tokens() -> None:
    assert create_access_token(1) != create_access_token(2)


def test_invalid_token_raises_401() -> None:
    with pytest.raises(HTTPException) as exc:
        _decode_token("not.a.valid.jwt")
    assert exc.value.status_code == 401


def test_tampered_token_raises_401() -> None:
    token = create_access_token(1)
    tampered = token[:-4] + "xxxx"
    with pytest.raises(HTTPException) as exc:
        _decode_token(tampered)
    assert exc.value.status_code == 401


def test_missing_cookie_raises_401() -> None:
    with pytest.raises(HTTPException) as exc:
        get_current_user_id(access_token=None)
    assert exc.value.status_code == 401


def test_valid_cookie_returns_user_id() -> None:
    token = create_access_token(7)
    assert get_current_user_id(access_token=token) == 7
