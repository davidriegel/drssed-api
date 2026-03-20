from flask import Blueprint, jsonify, send_from_directory
from app.utils.limiter import limiter
from app.utils.logging import get_logger

uploads = Blueprint("uploads", __name__)
logger = get_logger()

#@uploads.route('/profile_pictures/default/<filename>.png', methods=['GET'])
#@uploads.route('/profile_pictures/<user_id>.webp', methods=['GET'])
#@uploads.route('/profile_pictures/<user_id>', methods=['GET'])
#@limiter.limit("3 per minute")
#def getProfilePicture(user_id=None, filename=None):
#    try:
#        if filename:
#            return send_from_directory('app/static/profile_pictures/default', f'{filename}.png')
#        
#        return send_from_directory('app/static/profile_pictures', f'{user_id}.webp')
#    except NotFound:
#        try:
#            return send_from_directory(user_manager.getUserProfilePicture(user_id))
#        except UserNotFoundError as e:
#            return send_from_directory('app/static/profile_pictures/default', f'{user_id}.png')
#        except Exception as e:
#            logger.error(f"An unexpected error occurred: {e}")
#            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
#    except Exception as e:
#        logger.error(f"An unexpected error occurred: {e}")
#        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@uploads.route('/clothing_images/<clothing_id>.webp', methods=['GET'])
@uploads.route('/clothing_images/<clothing_id>', methods=['GET'])
@limiter.limit("10 per minute")
def getClothingImage(clothing_id):
    try:
        return send_from_directory('app/static/clothing_images', f'{clothing_id}.webp')
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@uploads.route('/temp/<filename>', methods=['GET'])
@limiter.limit("2 per minute")
def getTempImage(filename):
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    filename = filename.strip() + ".webp" if not filename.endswith(".webp") else filename

    try:
        return send_from_directory('app/static/temp', f'{filename}')
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@uploads.get('/outfit_images/<filename>')
@limiter.limit("10 per minute")
def get_outfit_image(filename):
    filename = filename.strip() + ".webp" if not filename.endswith(".webp") else filename

    try:
        return send_from_directory('app/static/outfit_collages', f'{filename}')
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@uploads.get('/openapi.yaml')
def get_openapi_spec():
    return send_from_directory('app/static', 'openapi.yaml')