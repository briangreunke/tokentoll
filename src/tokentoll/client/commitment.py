from __future__ import annotations

import hashlib
import json
import secrets


def compute_commitment(
    answers: dict[str, str], nonce: str | None = None
) -> tuple[str, str]:
    """Compute commitment hash for answers.

    Returns (commitment_hex, nonce). If nonce is None, generates a random one.
    """
    if nonce is None:
        nonce = secrets.token_hex(16)
    canonical = json.dumps(answers, sort_keys=True, separators=(",", ":"))
    commitment = hashlib.sha256((canonical + nonce).encode()).hexdigest()
    return commitment, nonce
