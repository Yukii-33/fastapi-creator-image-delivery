import asyncio
from io import BytesIO
from unittest.mock import AsyncMock, patch

from PIL import Image
from fastapi import FastAPI

from src.creator_delivery import make_delivery_image
from src.media_ingestion import BUCKET, lifespan


def test_landscape_upload_is_bounded_without_upscaling() -> None:
    source = BytesIO()
    Image.new("RGB", (2400, 1200), "#c84b31").save(source, format="PNG")

    result = make_delivery_image(source.getvalue(), max_edge=600)

    assert (result.width, result.height) == (600, 300)
    assert result.content_type == "image/jpeg"
    with Image.open(BytesIO(result.data)) as delivered:
        assert delivered.format == "JPEG"


def test_small_upload_keeps_its_dimensions() -> None:
    source = BytesIO()
    Image.new("RGB", (320, 180), "white").save(source, format="PNG")

    result = make_delivery_image(source.getvalue(), max_edge=600)

    assert (result.width, result.height) == (320, 180)


def test_startup_uses_non_mutating_presign_probe() -> None:
    async def start_and_stop() -> AsyncMock:
        storage = AsyncMock()
        with patch("src.media_ingestion.InfraiStorage", return_value=storage):
            async with lifespan(FastAPI()):
                pass
        return storage

    storage = asyncio.run(start_and_stop())
    storage.presign_get.assert_awaited_once_with(BUCKET, ".infrai-startup-check")
    storage.create_bucket.assert_not_awaited()
    storage.close.assert_awaited_once()
