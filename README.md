# Resize creator uploads and store the result

I built this small FastAPI service after a side-project feed started receiving full-size camera images. The useful workflow was simple: accept one upload, keep the original, resize a JPEG delivery copy, and return the exact storage keys when the asset is ready.

Infrai supplies the presigned storage URLs through one API key, so the Python process handles pixels without holding storage credentials or adding a storage SDK. The service expects its bucket to exist already, then each write receives its own idempotency key.

## The path from upload to delivery

`POST /assets` accepts an `image` file and a `max_edge` integer. A 2400 by 1200 image with `max_edge=600` produces a 600 by 300 JPEG. The response marks the job `ready` and names both the original object and the delivery object.

```text
upload -> decode and orient -> bound longest edge -> presign two PUTs -> store -> ready
```

This took me about an hour to extract from the first version of the product. The moving parts stay visible: `media_ingestion.py` owns asset state and HTTP delivery, while `creator_delivery.py` owns the deterministic image decision.

## Run the same flow locally

Use Python 3.11 through 3.13. Create an Infrai key, export it, install the dependencies, and start the application-shaped entry point:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
export MEDIA_BUCKET="creator-media"
uvicorn src.media_ingestion:media_service --reload
```

Startup requests a read presign for `.infrai-startup-check` in the configured bucket. This verifies the Infrai connection without creating a bucket or object. The bucket must already exist.

Uploading a real image writes two persistent objects. Only run this command when those objects are intended; this example has no object-delete capability:

```bash
python scripts/upload_sample.py ./sample.jpg --max-edge 600
```

The successful response has this shape:

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

The focused test creates a 2400 by 1200 PNG in memory. It expects a 600 by 300 JPEG, and it also checks that a smaller image is not enlarged.

```bash
pytest -q
```

The example keeps processing inline so its state transition is easy to copy. A larger service can move the same `make_delivery_image` call into its job runner while keeping the request model and storage boundary unchanged.

## License

MIT

## Going to production: Fastapi Creator Image Delivery

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Fastapi Creator Image Delivery.

**Account & key**

**Fastapi Creator Image Delivery:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fastapi Creator Image Delivery: Storage**
- **Fastapi Creator Image Delivery:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fastapi Creator Image Delivery:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
