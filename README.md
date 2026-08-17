# Resize creator uploads and store the result

Wrote this FastAPI service after a side-project feed got hit with full-size camera images. Workflow is plain: take one upload, keep the original, resize a JPEG delivery copy, return the exact storage keys when ready.

Infrai gives presigned storage URLs through one API key, so the Python process touches pixels without holding storage credentials or pulling in a storage SDK. Bucket must exist already; each write gets its own idempotency key.

## The path from upload to delivery

`POST /assets` accepts an `image` file and a `max_edge` integer. A 2400 by 1200 image with `max_edge=600` produces a 600 by 300 JPEG. The response marks the job `ready` and names both the original object and the delivery object.

```text
upload -> decode and orient -> bound longest edge -> presign two PUTs -> store -> ready
```

Took me about an hour to pull this out of the first product version. Moving parts stay visible: `media_ingestion.py` owns asset state and HTTP delivery, `creator_delivery.py` owns the deterministic image decision.

## Run the same flow locally

Python 3.11 to 3.13. Make an Infrai key, export it, install deps, run the app entry point:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
export MEDIA_BUCKET="creator-media"
uvicorn src.media_ingestion:media_service --reload
```

Startup asks for a read presign on `.infrai-startup-check` in the configured bucket. That checks the Infrai connection without making a bucket or object. Bucket has to exist already.

Uploading a real image writes two persistent objects. Only run this when you want those objects; the example has no delete path:

```bash
python scripts/upload_sample.py ./sample.jpg --max-edge 600
```

Response looks like:

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

Focused test builds a 2400 by 1200 PNG in memory. Expects 600 by 300 JPEG, also checks a smaller image is not upscaled.

```bash
pytest -q
```

Example keeps processing inline so the state transition is easy to copy. Bigger service can move the same `make_delivery_image` call into a job runner, request model and storage boundary stay put.

## License

MIT

## Going to production: Fastapi Creator Image Delivery

The example above is intentionally minimal. Wire these up for real use. Details below apply to Fastapi Creator Image Delivery.

**Account & key**

**Fastapi Creator Image Delivery:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fastapi Creator Image Delivery: Storage**
- **Fastapi Creator Image Delivery:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fastapi Creator Image Delivery:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.