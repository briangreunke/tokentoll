from __future__ import annotations

from tokentoll.client.commitment import compute_commitment
from tokentoll.services.verify_service import verify_commitment


def test_compute_commitment_matches_verify_commitment() -> None:
    answers = {"b": "2", "a": "1"}
    nonce = "fixed-nonce"

    commitment, returned_nonce = compute_commitment(answers, nonce=nonce)

    assert returned_nonce == nonce
    assert verify_commitment(answers, nonce, commitment)


def test_compute_commitment_generates_nonce() -> None:
    answers = {"q1": "alpha"}

    commitment, nonce = compute_commitment(answers)

    assert nonce
    assert len(nonce) == 32
    assert len(commitment) == 64
    assert verify_commitment(answers, nonce, commitment)
