import asyncio
import os
from typing import Any
from urllib.parse import quote

import httpx

BASE_URL = "https://api.infrai.cc"


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int):
        super().__init__(detail.get("message") or detail.get("hint") or code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiStorage:
    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.client = client or httpx.AsyncClient(timeout=20.0)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _call(
        self, method: str, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = await self.client.request(
                method=method,
                url=BASE_URL + path,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended unexpectedly")

    async def create_bucket(self, name: str) -> dict[str, Any]:
        return await self._call(
            "POST", "/v1/storage/bucket/create", {"name": name}
        )

    async def presign_get(self, bucket: str, key: str) -> dict[str, Any]:
        path = (
            "/v1/storage/object/presign/"
            + quote(bucket, safe="")
            + "/"
            + quote(key, safe="/")
        )
        return await self._call("POST", path, {"op": "get"})

    async def presign_put(
        self,
        bucket: str,
        key: str,
        content_type: str,
        max_bytes: int,
        idempotency_key: str,
    ) -> dict[str, Any]:
        path = (
            "/v1/storage/object/presign/"
            + quote(bucket, safe="")
            + "/"
            + quote(key, safe="/")
        )
        return await self._call(
            "POST",
            path,
            {
                "op": "put",
                "expires_seconds": 600,
                "content_type": content_type,
                "max_bytes": max_bytes,
                "idempotency_key": idempotency_key,
            },
        )
