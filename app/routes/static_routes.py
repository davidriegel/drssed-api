from flask import Blueprint, jsonify, send_from_directory
from app.utils.limiter import limiter
from app.utils.logging import get_logger

static = Blueprint("static", __name__)
logger = get_logger()

@static.route('/clothing_images/<clothing_id>.webp', methods=['GET'])
@static.route('/clothing_images/<clothing_id>', methods=['GET'])
@limiter.limit("10 per minute")
def getClothingImage(clothing_id):
    try:
        return send_from_directory('app/static/clothing_images', f'{clothing_id}.webp')
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@static.route('/temp/<filename>', methods=['GET'])
@limiter.limit("2 per minute")
def getTempImage(filename):
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    filename = filename.strip() + ".webp" if not filename.endswith(".webp") else filename

    try:
        return send_from_directory('app/static/temp', f'{filename}')
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": "File not found."}), 500

@static.route('/outfit_images/<filename>', methods=['GET'])
@limiter.limit("10 per minute")
def get_outfit_image(filename):
    filename = filename.strip() + ".webp" if not filename.endswith(".webp") else filename

    try:
        return send_from_directory('app/static/outfit_collages', f'{filename}')
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500