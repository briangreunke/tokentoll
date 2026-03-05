from __future__ import annotations

from types import TracebackType

import httpx

from tokentoll.client.commitment import compute_commitment
from tokentoll.client.types import Challenge, VerificationResult


class TokenTollClient:
    """Client for agents to interact with TokenToll."""

    def __init__(
        self,
        base_url: str,
        site_key: str,
        http_client: httpx.AsyncClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.site_key = site_key
        self._owns_client = http_client is None
        if http_client is None:
            self._http = httpx.AsyncClient(
                base_url=self.base_url, transport=transport
            )
        else:
            self._http = http_client

    async def get_challenge(self) -> Challenge:
        """Request a new challenge from TokenToll."""
        response = await self._http.post(
            "/challenge", json={"site_key": self.site_key}
        )
        response.raise_for_status()
        data = response.json()
        return Challenge(**data)

    async def submit_answers(
        self, challenge_id: str, answers: dict[str, str]
    ) -> VerificationResult:
        """Submit answers and receive verification result."""
        commitment, nonce = compute_commitment(answers)
        response = await self._http.post(
            "/verify",
            json={
                "challenge_id": challenge_id,
                "nonce": nonce,
                "answers": answers,
                "commitment": commitment,
            },
        )
        response.raise_for_status()
        data = response.json()
        return VerificationResult(**data)

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> "TokenTollClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
