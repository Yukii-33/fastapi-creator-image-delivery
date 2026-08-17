import argparse
import json
import mimetypes
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload one creator image")
    parser.add_argument("image", type=Path)
    parser.add_argument("--max-edge", type=int, default=1280)
    parser.add_argument("--service", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    content_type = mimetypes.guess_type(args.image.name)[0] or "application/octet-stream"
    with args.image.open("rb") as source:
        response = httpx.request(
            method="POST",
            url=f"{args.service}/assets",
            data={"max_edge": str(args.max_edge)},
            files={"image": (args.image.name, source, content_type)},
            timeout=60.0,
        )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()

