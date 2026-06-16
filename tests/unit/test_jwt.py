"""Tests unitarios — JWT service."""
import uuid
import pytest
from fastapi import HTTPException
from app.services.jwt_service import create_access_token, create_refresh_token, decode_token
from app.constants import UserRole


class TestJwtService:
    def test_access_token_roundtrip(self):
        user_id = str(uuid.uuid4())
        token, jti = create_access_token(user_id, UserRole.CLIENT)
        data = decode_token(token)
        assert data.sub == user_id
        assert data.role == UserRole.CLIENT
        assert data.jti == jti

    def test_refresh_token_roundtrip(self):
        user_id = str(uuid.uuid4())
        token, jti = create_refresh_token(user_id, UserRole.PROVIDER)
        data = decode_token(token)
        assert data.sub == user_id
        assert data.jti == jti

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token, _ = create_access_token(str(uuid.uuid4()), UserRole.CLIENT)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered)
        assert exc_info.value.status_code == 401

    def test_different_users_get_different_jtis(self):
        _, jti1 = create_access_token(str(uuid.uuid4()), UserRole.CLIENT)
        _, jti2 = create_access_token(str(uuid.uuid4()), UserRole.CLIENT)
        assert jti1 != jti2
