import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify
from app.utils.limiter import limiter
from app.utils.logging import get_logger
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    PermissionError
)
import traceback
from app.utils.authentication_managment import authentication_manager
from app.utils.user_managment import user_manager
from app.utils.clothing_managment import clothing_manager
from app.utils.outfit_managment import outfit_manager
from app.main.routes import api as main
from app.auth.routes import auth
from app.users.routes import users
from app.uploads.routes import uploads
from app.clothing.routes import clothing
from app.images.routes import images
from app.outfits.routes import outfits

api = Flask("Clothing Booth API")
logger = get_logger()

def prepare_api():
    limiter.init_app(api)

    prepare_static_directories()
    register_blueprints()
    logger.debug("API prepared successfully.")

@api.errorhandler(ValidationError)
def validation_error_handler(error):
    return jsonify({"error": str(error)}), 400

@api.errorhandler(NotFoundError)
def not_found_error_handler(error):
    return jsonify({"error": str(error)}), 404

@api.errorhandler(ConflictError)
def conflict_error_handler(error):
    return jsonify({"error": str(error)}), 409

@api.errorhandler(PermissionError)
def outfit_permission_error_handler(error):
    return jsonify({"error": str(error)}), 403

@api.errorhandler(Exception)
def internal_error_handler(error):
    logger.debug(error)
    logger.debug(traceback.format_exc())
    return jsonify({"error": "An unexpected error occurred."}), 500

@api.errorhandler(404)
def not_found_error_handler(error):
    return jsonify({"error": "Resource not found."}), 404

@api.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed."}), 405
    
def register_blueprints():
    api.register_blueprint(main, url_prefix="/")
    api.register_blueprint(auth, url_prefix="/auth")
    api.register_blueprint(users, url_prefix="/users")
    api.register_blueprint(clothing, url_prefix="/clothing")
    api.register_blueprint(uploads, url_prefix="/uploads")
    api.register_blueprint(images, url_prefix="/images")
    api.register_blueprint(outfits, url_prefix="/outfits")

    logger.debug("Blueprint routes registered")

def prepare_static_directories():
    static_dirs = ["app/static/clothing_images", "app/static/profile_pictures", "app/static/temp", "app/static/outfit_collages"]
    for directory in static_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as e:
                logger.critical(f"Error creating directory {directory}: {e}")
            else:
                logger.warning(f"New {directory} directory created.")

if __name__ != '__main__':
    prepare_api()
    logger.info("-- 🚀 Started API --")
else:
    logger.warning("-- ⚠️ API HAS TO BE STARTED THROUGH GUNICORN --")