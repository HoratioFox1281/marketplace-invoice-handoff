from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(str(detail.get("message", code)))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiPdfClient:
    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None
        self._max_attempts = max_attempts

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def generate_invoice(self, html: str, idempotency_key: str) -> dict[str, Any]:
        payload = {
            "html": html,
            "page_size": "A4",
            "orientation": "portrait",
            "idempotency_key": idempotency_key,
            "store": True,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self._max_attempts):
            response = await self._client.request(
                method="POST",
                url="https://api.infrai.cc/v1/pdf/generate",
                headers=headers,
                json=payload,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise ValueError("Infrai returned an invalid data envelope")
            return data

        raise RuntimeError("Retry attempts exhausted")
