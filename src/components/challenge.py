import base64
import hashlib
import secrets
import hmac


def make_nonce() -> str:
    raw = secrets.token_bytes(16)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")

def sign(secret: str, msg: str):
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

def compare_entries(a: str, b: str):
    return hmac.compare_digest(a, b)