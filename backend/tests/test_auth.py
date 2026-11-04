import pytest
from app.core.security import verify_password, create_access_token, decode_access_token

@pytest.mark.asyncio
async def test_password_hashing():
    raw_pass = "admin_secure_pass_2026"
    from app.core.security import get_password_hash
    hashed = get_password_hash(raw_pass)
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("wrong_password", hashed) is False

@pytest.mark.asyncio
async def test_jwt_token_generation_and_decode():
    email = "admin@replybd.com"
    token = create_access_token(subject=email)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == email
