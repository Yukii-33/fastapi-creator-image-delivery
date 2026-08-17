import hashlib
import os
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .creator_delivery import make_delivery_image
from .infrai_storage import InfraiError, InfraiStorage

BUCKET = os.environ.get("MEDIA_BUCKET", "creator-media")


class AssetDelivery(BaseModel):
    asset_id: str
    status: str
    original_key: str
    delivery_key: str
    width: int
    height: int


class ProcessingJob(BaseModel):
    max_edge: int = Field(1280, ge=64, le=4096)


async def put_signed(url: str, content: bytes, content_type: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method="PUT",
            url=url,
            headers={"Content-Type": content_type},
            content=content,
        )
        response.raise_for_status()


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = InfraiStorage()
    await storage.presign_get(BUCKET, ".infrai-startup-check")
    app.state.storage = storage
    try:
        yield
    finally:
        await storage.close()


media_service = FastAPI(title="Creator media delivery", lifespan=lifespan)


@media_service.post("/assets", response_model=AssetDelivery, status_code=201)
async def ingest_asset(
    image: UploadFile = File(...), max_edge: int = Form(1280)
) -> AssetDelivery:
    job = ProcessingJob(max_edge=max_edge)
    source = await image.read()
    if not source:
        raise HTTPException(status_code=400, detail="Image is empty")

    asset_id = uuid4().hex
    digest = hashlib.sha256(source).hexdigest()[:16]
    original_key = f"assets/{asset_id}/original"
    delivery_key = f"assets/{asset_id}/delivery-{job.max_edge}.jpg"

    try:
        delivery = make_delivery_image(source, job.max_edge)
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Upload must be a readable image") from exc

    storage: InfraiStorage = media_service.state.storage
    try:
        original_signing = await storage.presign_put(
            BUCKET,
            original_key,
            image.content_type or "application/octet-stream",
            len(source),
            f"{digest}-original",
        )
        delivery_signing = await storage.presign_put(
            BUCKET,
            delivery_key,
            delivery.content_type,
            len(delivery.data),
            f"{digest}-delivery-{job.max_edge}",
        )
        await put_signed(original_signing["url"], source, image.content_type or "application/octet-stream")
        await put_signed(delivery_signing["url"], delivery.data, delivery.content_type)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc

    return AssetDelivery(
        asset_id=asset_id,
        status="ready",
        original_key=original_key,
        delivery_key=delivery_key,
        width=delivery.width,
        height=delivery.height,
    )
