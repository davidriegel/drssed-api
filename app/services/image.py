__all__ = [
    "move_preview_image_to_permanent",
    "save_outfit_preview",
    "load_clothing_image_by_id",
    "generate_outfit_preview",
    "delete_outfit_preview",
    "delete_clothing_image",
]

import math
import os
from urllib.parse import urljoin

from PIL import Image
from werkzeug.datastructures import FileStorage

from app.core.logging import get_logger

logger = get_logger()


def move_preview_image_to_permanent(
    filename: str | None, is_clothing: bool = True
) -> str:
    if not filename:
        raise ValueError("Filename cannot be empty.")

    if not filename.endswith(".webp"):
        filename = filename + ".webp"

    try:
        src = f"app/static/temp/{filename}"
        dst = (
            f"app/static/clothing_images/{filename}"
            if is_clothing
            else f"app/static/profile_pictures/{filename}"
        )
        if not os.path.exists(src):
            raise FileNotFoundError(f"The temporary image {src} does not exist.")
        os.rename(src, dst)
        return dst
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while moving the image: {e}")
        raise


def save_outfit_preview(outfit_id: str, preview_file: FileStorage) -> str:
    """
    Returns: public_url
    """
    mimetype = (preview_file.mimetype or "").lower()
    if mimetype not in ("image/png", "image/webp", "image/jpeg", "image/jpg"):
        raise ValueError("Invalid preview mimetype. Must be png/webp/jpeg.")

    preview_file.stream.seek(0)
    img = Image.open(preview_file.stream).convert("RGBA")

    img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)

    path = f"app/static/outfit_collages/{outfit_id}.webp"
    img.save(path, "WEBP")

    return str(
        urljoin(
            os.getenv("API_BASE_URL", ""),
            f"static/outfit_collages/{outfit_id}.webp",
        )
    )


def load_clothing_image_by_id(image_id: str) -> Image.Image:
    image_path = os.path.join("app/static/clothing_images", f"{image_id}.webp")

    if not os.path.exists(image_path):
        raise FileNotFoundError("Image file missing")

    return Image.open(image_path)


def generate_outfit_preview(outfit_id: str, items: list[dict]) -> str:
    """
    Returns: public_url
    """
    canvas_width = 1024
    canvas_height = int(canvas_width * 4 / 3)

    canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))

    items.sort(key=lambda x: x["item"]["z"])

    for entry in items:
        _place_item(canvas, entry["item"], entry["image_id"])

    path = f"app/static/outfit_collages/{outfit_id}.webp"
    canvas.save(path, "WEBP")

    return str(
        urljoin(
            os.getenv("API_BASE_URL", ""),
            f"static/outfit_collages/{outfit_id}.webp",
        )
    )


def _place_item(canvas: Image.Image, item_data: dict, image_id: str):
    image = load_clothing_image_by_id(image_id)

    target_width = item_data["scale"] * canvas.width
    aspect = image.height / image.width
    target_height = target_width * aspect

    image = image.resize((int(target_width), int(target_height)), Image.LANCZOS)
    image = image.rotate(-math.degrees(item_data["rotation"]), expand=True)

    center_x = item_data["x"] * canvas.width
    center_y = item_data["y"] * canvas.height

    paste_x = int(center_x - image.width / 2)
    paste_y = int(center_y - image.height / 2)

    canvas.paste(image, (paste_x, paste_y), image)


def delete_outfit_preview(outfit_id: str) -> None:
    try:
        image_path = f"app/static/outfit_collages/{outfit_id}.webp"
        os.remove(image_path)
        logger.debug(f"Successfully deleted preview from: {outfit_id}")
    except FileNotFoundError:
        logger.debug(f"Preview file not found (already deleted): {outfit_id}")
    except PermissionError:
        logger.error(
            f"Permission denied while deleting preview from outfit: {outfit_id}",
            extra={"outfit_id": outfit_id},
        )
    except Exception as e:
        logger.error(
            f"Unexpected error while deleting preview from outfit {outfit_id}: {e}",
            exc_info=True,
            extra={"outfit_id": outfit_id},
        )
        raise


def delete_clothing_image(image_id: str) -> None:
    try:
        image_path = f"app/static/clothing_images/{image_id}.webp"
        os.remove(image_path)
        logger.debug(f"Successfully deleted image: {image_id}")
    except FileNotFoundError:
        logger.debug(f"Image file not found (already deleted): {image_id}")
    except PermissionError:
        logger.error(
            f"Permission denied while deleting image: {image_id}",
            extra={"image_id": image_id},
        )
    except Exception as e:
        logger.error(
            f"Unexpected error while deleting image {image_id}: {e}",
            exc_info=True,
            extra={"image_id": image_id},
        )
        raise
