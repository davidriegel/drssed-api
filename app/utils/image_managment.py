__all__ = ["image_manager"]

import traceback
import uuid
import os
from typing import Optional
from app.utils.exceptions import ImageUnclearError, UnsupportedFileTypeError, FileTooLargeError
from werkzeug.datastructures import FileStorage
from PIL import Image
from io import BytesIO
from backgroundremover import bg
from app.utils.logging import get_logger
from app.models.clothing import ClothingCategory
from urllib.parse import urljoin

from sklearn.cluster import KMeans

from fashion_clip.fashion_clip import FashionCLIP
import numpy as np

fclip = FashionCLIP("fashion-clip")

logger = get_logger()

CATEGORIES = [category.value for category in ClothingCategory]

class ImageManager:
    
    def process_image_preview(self, file: Optional[FileStorage]) -> tuple[str, str, str, str, list[str], list[str]]:
        if not isinstance(file, FileStorage) or not isinstance(file.filename, str) or not file.filename.endswith((".png", ".jpg", ".jpeg")):
            raise UnsupportedFileTypeError("The file provided is not a supported image type. Supported types are PNG, JPG, and JPEG.")
        
        if len(file.read()) > 4*1024*1024:
            raise FileTooLargeError("File is too large (max 4MB)")
        
        file.seek(0)
        
        image_id = str(uuid.uuid4())
        image_path = f"app/static/temp/" + image_id + ".webp"
        processed_image = self._extract_foreground(file)
        
        processed_image.save(image_path, format="WEBP")
        
        dominant_hexcode = self._extract_dominant_color(processed_image)
        
        clothing_category = self._extract_clothing_category(image_path)
        
        image_url = str(urljoin(os.getenv("API_BASE_URL", ""), f"uploads/temp/{image_id}.webp"))
        
        return image_url, image_id, dominant_hexcode, clothing_category, [], []
    
    def _extract_clothing_category(self, image_path: str) -> str:
        image_emb = fclip.encode_images([image_path], batch_size=1)
        text_emb = fclip.encode_text(CATEGORIES, batch_size=1)
        
        sims = (image_emb @ text_emb.T).squeeze(0)
        best_idx = int(np.argmax(sims))
        predicted_category = CATEGORIES[best_idx]
        
        return predicted_category
        
    def _extract_dominant_color(self, image: Image.Image) -> str:
        arr = np.array(image.resize((100, 100)))
        
        rgb = arr[:, :, :3].reshape(-1, 3)
        alpha = arr[:, :, 3].reshape(-1)

        mask = alpha > 10 # remove half-transparent pixels
        rgb = rgb[mask]
        
        if len(rgb) == 0:
            return "#000000"
        
        dominant_color = tuple(KMeans(n_clusters=1, random_state=0).fit(rgb).cluster_centers_[0].astype(int))
        dominant_color_hex = '#{:02X}{:02X}{:02X}'.format(*dominant_color)
        
        return dominant_color_hex

    def _extract_foreground(self, file: Optional[FileStorage]) -> Image.Image:
        try:
            image = Image.open(file)
            image = image.convert("RGBA")
            
            pngImage = BytesIO()
            image.save(pngImage, format="PNG")
            pngImage.seek(0)
            
            try:
                without_background = bg.remove(pngImage.read(), model_name="u2net_cloth_segm",
                                        alpha_matting=True,
                                        alpha_matting_foreground_threshold=200, # 240
                                        alpha_matting_background_threshold=10, #30 # 10
                                        alpha_matting_erode_structure_size=13, #5 # 10
                                        alpha_matting_base_size=512, # 1000
                                        )
            except ValueError as e:
                raise ImageUnclearError("The provided image does not contain a foreground.")
            except Exception as e:
                logger.error(f"An unexpected error occured while removing the background of an image: {e}")
                logger.error(traceback.format_exc())
                raise e

            new_image = Image.open(BytesIO(without_background))
            
            alpha = new_image.getchannel("A")
            bbox = alpha.getbbox()
            
            cropped_image = new_image.crop(bbox)
            
            return cropped_image
        except Exception as e:
            logger.error(f"An unexpected error occured while removing the background of an image: {e}")
            logger.error(traceback.format_exc())
            raise e

    def move_preview_image_to_permanent(self, filename: Optional[str], is_clothing: bool = True) -> str:
        if not filename:
            raise ValueError("Filename cannot be empty.")
        
        if not filename.endswith(".webp"):
            filename = filename + ".webp"
        
        try:
            src = f"app/static/temp/{filename}"
            dst = f"app/static/clothing_images/{filename}" if is_clothing else f"app/static/profile_pictures/{filename}"
            if not os.path.exists(src):
                raise FileNotFoundError(f"The temporary image {src} does not exist.")
            os.rename(src, dst)
            return dst
        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while moving the image: {e}")
            raise e
            
    # ! DELETION of old temp images
    
    def save_outfit_preview(self, preview_file: FileStorage) -> tuple[str, str]:
        """
        Returns: (public_url, image_id)
        """
        
        mimetype = (preview_file.mimetype or "").lower()
        if mimetype not in ("image/png", "image/webp", "image/jpeg", "image/jpg"):
            raise ValueError("Invalid preview mimetype. Must be png/webp/jpeg.")

        preview_file.stream.seek(0)
        img = Image.open(preview_file.stream).convert("RGBA")

        max_size = (1024, 1024)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        alpha = img.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            img = img.crop(bbox)

        filename = str(uuid.uuid4())
        path = f"app/static/outfit_collages/{filename}.webp"
        img.save(path, "WEBP")  # optional: quality=85, method=6

        public_url = str(urljoin(os.getenv("API_BASE_URL", ""), f"uploads/outfit_collages/{filename}.webp"))
        return public_url, filename
    
    def load_clothing_image_by_id(self, image_id: str) -> Image.Image:
        image_path = os.path.join(
            "app/static/clothing_images",
            f"{image_id}.webp"
        )

        if not os.path.exists(image_path):
            raise FileNotFoundError("Image file missing")

        return Image.open(image_path)
    
    def generate_outfit_preview(self, items: list[dict]) -> tuple[str, str]:
        """
        Returns: (public_url, image_id)
        """
        
        canvas_width = 1024
        canvas_height = 1024

        canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
        
        items.sort(key=lambda x: x["item"]["z"])

        for entry in items:
            self._place_item(
                canvas,
                entry["item"],
                entry["image_id"]
            )
        
        filename = str(uuid.uuid4())
        path = f"app/static/outfit_collages/{filename}.webp"
        canvas.save(path, "WEBP")
        
        public_url = str(urljoin(os.getenv("API_BASE_URL", ""), f"uploads/outfit_collages/{filename}.webp"))
        return public_url, filename
        
    def _place_item(self, canvas: Image.Image, item_data: dict, image_id: str):
        image = self.load_clothing_image_by_id(image_id)
        
        target_width = item_data["scale"] * canvas.width

        aspect = image.height / image.width
        target_height = target_width * aspect

        image = image.resize((int(target_width), int(target_height)), Image.LANCZOS)
        
        image = image.rotate(-item_data["rotation"], expand=True)
        
        center_x = item_data["x"] * canvas.width
        center_y = item_data["y"] * canvas.height
        
        paste_x = int(center_x - image.width / 2)
        paste_y = int(center_y - image.height / 2)
        
        canvas.paste(image, (paste_x, paste_y), image)
    
    def delete_outfit_preview(self, image_id: str):
        os.remove(f"app/static/outfit_collages/{image_id}.webp")
    
image_manager = ImageManager()