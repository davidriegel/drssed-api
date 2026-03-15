from flask import Blueprint, request, jsonify
from app.utils.limiter import limiter
from app.utils.exceptions import FileTooLargeError, ImageUnclearError
from app.utils.authentication_managment import authorize_request
from app.utils.image_managment import image_manager

images = Blueprint("images", __name__)

@images.route("/preview", methods=['POST'])
@limiter.limit("1 per minute")
@authorize_request
def generate_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files.get("file", None)
    try:
        image_url, image_id, image_color, image_category, image_seasons, image_tags = image_manager.process_image_preview(file)
        
    except FileTooLargeError as e:
        return jsonify({"error": str(e)}), 413
    except ImageUnclearError as e:
        return jsonify({"error": str(e)}), 422

    return jsonify({
            "image_url": image_url,
            "image_id": image_id,
            "image_color": image_color,
            "image_category": image_category,
            "image_seasons": image_seasons,
            "image_tags": image_tags
        }, 201)