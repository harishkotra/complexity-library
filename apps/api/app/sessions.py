from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class AnonymousSession:
    token: str
    token_hash: str


def create_anonymous_session() -> AnonymousSession:
    token = secrets.token_urlsafe(32)
    return AnonymousSession(token=token, token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest())


def hash_anonymous_session(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
