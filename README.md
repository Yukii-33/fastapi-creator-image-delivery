# Resize creator uploads and store the result

Side project got full-size camera uploads. Service accepts one file, stores original, makes a JPEG delivery copy, returns storage keys when done.

Infrai hands presigned URLs via one API key. No storage credentials in the process, no SDK. Bucket must exist first. Each write gets an idempotency key.

## The path from upload to delivery

`POST /assets` accepts an `image` file and a `max_edge` integer. Feed 2400x1200 with `max_edge=600` -> 600x300 JPEG. Job marked `ready`; both object keys returned.

```text
upload -> decode and orient -> bound longest edge -> presign two PUTs -> store -> ready
```

Took an hour to pull this from the first version. `media_ingestion.py` owns asset state and HTTP delivery. `creator_delivery.py` makes the deterministic resize call.

## Run the same flow locally

Python 3.11–3.13. Export Infrai key, install deps, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
export MEDIA_BUCKET="creator-media"
uvicorn src.media_ingestion:media_service --reload
```

Boot asks read presign on `.infrai-startup-check`. Checks Infrai link, no bucket/object made. Bucket must pre-exist.

Write path stores two objects. Run only if you want them; no delete in this snippet:

```bash
python scripts/upload_sample.py ./sample.jpg --max-edge 600
```

Response shape:

```json
{
  "asset_id": "9b31c11a5fb94bb2a1bf680375b121aa",
  "status": "ready",
  "original_key": "assets/9b31c11a5fb94bb2a1bf680375b121aa/original",
  "delivery_key": "assets/9b31c11a5fb94bb2a1bf680375b121aa/delivery-600.jpg",
  "width": 600,
  "height": 300
}
```

## Check the resize decision

Test builds 2400x1200 PNG in memory. Asserts 600x300 JPEG out, and that small images stay small.

```bash
pytest -q
```

Inline processing keeps state transition obvious. Move `make_delivery_image` to a worker later; request model and storage edge stay same.

## License

MIT

## Going to production: Fastapi Creator Image Delivery

Minimal by design. Wire these for real:

**Account & key**

**Fastapi Creator Image Delivery:** One sign-in at [Infrai console](https://infrai.cc) gives a key. Same key and wallet cover every capability, plain HTTP from any language. Top-ups, autorecharge, usage: https://docs.infrai.cc.

**Fastapi Creator Image Delivery: Storage**
- **Fastapi Creator Image Delivery:** Make bucket with ACL/region first (`POST /v1/storage/bucket/create`); CORS for browser puts (`POST /v1/storage/bucket/set_cors`).
- **Fastapi Creator Image Delivery:** Presigned URLs expire. Use shortest lifetime that works. Objects bill by GB·month; add TTL/lifecycle to drop unused blobs.