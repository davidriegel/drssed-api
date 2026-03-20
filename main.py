import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify
from app.utils.limiter import limiter
from app.utils.logging import get_logger, setup_logging
from app.utils.middleware.request_logger import init_request_logging
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    PermissionError
)
from app.utils.helpers import helper
from app.routes.main_routes import api as main
from app.routes.auth_routes import auth
from app.routes.users_routes import users
from app.routes.uploads_routes import uploads
from app.routes.clothing_routes import clothing
from app.routes.images_routes import images
from app.routes.outfits_routes import outfits

api = Flask("Drssed API")

setup_logging(api)
logger = get_logger("main")

def prepare_api():
    limiter.init_app(api)
    
    init_request_logging(api)

    prepare_static_directories()
    register_blueprints()
    logger.info("API prepared successfully.")

@api.errorhandler(ValidationError)
def validation_error_handler(error):
    logger.warning(f"Validation error: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": str(error)}), 400

@api.errorhandler(NotFoundError)
def not_found_error_handler(error):
    logger.warning(f"Resource not found: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": str(error)}), 404

@api.errorhandler(ConflictError)
def conflict_error_handler(error):
    logger.warning(f"Conflict: {str(error)}", extra=helper.get_request_context())
    return jsonify({"error": str(error)}), 409

@api.errorhandler(PermissionError)
def outfit_permission_error_handler(error):
    logger.warning(f"Permission denied: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": str(error)}), 403

@api.errorhandler(Exception)
def internal_error_handler(error):
    logger.exception(f"Unhandled exception: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": "An unexpected error occurred."}), 500

@api.errorhandler(404)
def not_found_error_handler(error):
    logger.info("404 - Route not found", extra=helper.get_request_context())
    
    return jsonify({"error": "Resource not found."}), 404

@api.errorhandler(405)
def method_not_allowed(error):
    logger.warning("405 - Method not allowed", extra=helper.get_request_context())
    
    return jsonify({"error": "Method not allowed."}), 405
    
def register_blueprints():
    api.register_blueprint(main, url_prefix="/")
    api.register_blueprint(auth, url_prefix="/auth")
    api.register_blueprint(users, url_prefix="/users")
    api.register_blueprint(clothing, url_prefix="/clothing")
    api.register_blueprint(uploads, url_prefix="/uploads")
    api.register_blueprint(images, url_prefix="/images")
    api.register_blueprint(outfits, url_prefix="/outfits")

    logger.info("Blueprint routes registered successfully")

def prepare_static_directories():
    static_dirs = ["app/static/clothing_images", "app/static/profile_pictures", "app/static/temp", "app/static/outfit_collages"]
    for directory in static_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            except OSError as e:
                logger.critical(f"Failed to create directory {directory}: {e}")

if __name__ != '__main__':
    prepare_api()
    logger.info("🚀 Started API successfully")
else:
    logger.warning("⚠️ API must be started through Gunicorn, not directly")