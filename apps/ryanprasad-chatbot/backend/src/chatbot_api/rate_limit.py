from __future__ import annotations

import hashlib


def build_rate_limit_key(identity: str, session_id: str, *, salt: str, now_epoch: int) -> dict[str, object]:
    digest = hashlib.sha256(f"{salt}:{identity}:{session_id}".encode("utf-8")).hexdigest()[:32]
    hour_bucket = now_epoch // 3600
    return {
        "pk": f"identity#{digest}",
        "sk": f"window#hour#{hour_bucket}",
        "ttl": now_epoch + 90000,
    }
