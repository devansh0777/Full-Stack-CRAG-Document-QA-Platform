from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hashing_roundtrip():
    password = "super-secret"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_access_token_roundtrip():
    token = create_access_token("123")
    payload = decode_access_token(token)
    assert payload["sub"] == "123"

