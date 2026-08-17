from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps


@dataclass(frozen=True)
class DeliveryImage:
    data: bytes
    width: int
    height: int
    content_type: str = "image/jpeg"


def make_delivery_image(source: bytes, max_edge: int) -> DeliveryImage:
    if max_edge < 64 or max_edge > 4096:
        raise ValueError("max_edge must be between 64 and 4096")

    with Image.open(BytesIO(source)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="JPEG", quality=86, optimize=True)
        width, height = image.size
    return DeliveryImage(output.getvalue(), width, height)

