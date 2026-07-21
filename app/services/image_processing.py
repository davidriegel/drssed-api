__all__ = ["process_image"]

import os
import traceback
import uuid

# Set tokenizers parallelism to false since gunicorn already uses multiple workers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Disable tqdm progress bars globally
from functools import partialmethod

from tqdm import tqdm

tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)

from io import BytesIO

import numpy as np
from backgroundremover import bg
from fashion_clip.fashion_clip import FashionCLIP
from PIL import Image
from sklearn.cluster import KMeans

from app.core.logging import get_logger
from app.models.clothing import ClothingCategory, ClothingSubCategory
from app.utils.exceptions import ImageUnclearError

model = FashionCLIP("fashion-clip")

logger = get_logger("image_processing")


def process_image(raw_image_path: str) -> dict:
    """
    RQ job: cut out foreground, categorize, extract dominant color.
    """
    logger.info(f"Processing image from {raw_image_path}")

    try:
        with open(raw_image_path, "rb") as f:
            processed_image = _extract_foreground(f)

        image_id = str(uuid.uuid4())
        image_path = f"app/static/temp/{image_id}.webp"
        processed_image.save(image_path, format="WEBP")

        dominant_hexcode = _extract_dominant_color(processed_image)
        category, sub_category = _extract_clothing_category(image_path)

        try:
            os.remove(raw_image_path)
        except FileNotFoundError:
            pass

        logger.info(f"Finished processing image {image_id}")

        return {
            "image_id": image_id,
            "dominant_hexcode": dominant_hexcode,
            "category": category.value,
            "sub_category": sub_category.value,
        }
    except ImageUnclearError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error while processing image: {e}")
        logger.error(traceback.format_exc())
        raise


def _extract_clothing_category(
    image_path: str,
) -> tuple[ClothingCategory, ClothingSubCategory]:
    image_emb = model.encode_images([image_path], batch_size=1)

    clothing_categories = [category.value for category in ClothingSubCategory]
    text_emb = model.encode_text(clothing_categories, batch_size=1)

    sims = (image_emb @ text_emb.T).squeeze(0)
    best_idx = int(np.argmax(sims))
    sub_category = ClothingSubCategory(clothing_categories[best_idx])
    category = sub_category.category

    return category, sub_category


def _extract_dominant_color(image: Image.Image) -> str:
    arr = np.array(image.resize((100, 100)))

    rgb = arr[:, :, :3].reshape(-1, 3)
    alpha = arr[:, :, 3].reshape(-1)

    mask = alpha > 10  # remove half-transparent pixels
    rgb = rgb[mask]

    if len(rgb) == 0:
        return "#000000"

    dominant_color = tuple(
        KMeans(n_clusters=1, random_state=0).fit(rgb).cluster_centers_[0].astype(int)
    )
    return "#{:02X}{:02X}{:02X}".format(*dominant_color)


def _extract_foreground(file) -> Image.Image:
    try:
        image: Image.Image = Image.open(file)
        image = image.convert("RGBA")

        max_size = 1024
        image.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)

        png_image = BytesIO()
        image.save(png_image, format="PNG")
        png_image.seek(0)

        try:
            without_background = bg.remove(
                png_image.read(),
                model_name="u2netp",
                alpha_matting=False,
                alpha_matting_foreground_threshold=200,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_structure_size=13,
                alpha_matting_base_size=512,
            )
        except ValueError:
            raise ImageUnclearError("The provided image does not contain a foreground.")

        new_image = Image.open(BytesIO(without_background))
        alpha = new_image.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            new_image = new_image.crop(bbox)

        return new_image
    except ImageUnclearError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error while removing background: {e}")
        logger.error(traceback.format_exc())
        raise
