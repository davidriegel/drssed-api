import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify
from app.core.limiter import limiter
from app.core.scheduler import init_scheduler, register_job
from app.core.logging import get_logger, setup_logging
from app.services.cleanup import create_cleanup_jobs
from app.utils.middleware.request_logger import init_request_logging
from app.utils.exceptions import (
    ValidationError,
    NotFoundError,
    ConflictError,
    PermissionError,
    UnauthorizedError
)
from app.utils.helpers import helper
from app.routes.main import api as main
from app.routes.health import health
from app.routes.auth import auth
from app.routes.users import users
from app.routes.static import static
from app.routes.clothing import clothing
from app.routes.images import images
from app.routes.outfits import outfits

api = Flask("Drssed API")

setup_logging(api)
logger = get_logger("main")

all_jobs = [*create_cleanup_jobs()]

def prepare_api():
    limiter.init_app(api)
    
    init_request_logging(api)
    init_scheduler(api)
    for job in all_jobs:
        register_job(job)

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
    
    response = {"error": str(error)}
    if hasattr(error, 'field') and error.field:
        response["field"] = error.field
        
    return jsonify(response), 409

@api.errorhandler(PermissionError)
def outfit_permission_error_handler(error):
    logger.warning(f"Permission denied: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": str(error)}), 403

@api.errorhandler(UnauthorizedError)
def unauthorized_error_handler(error):
    logger.warning(f"Unauthorized access: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": str(error)}), 401

@api.errorhandler(Exception)
def internal_error_handler(error):
    logger.exception(f"Unhandled exception: {str(error)}", extra=helper.get_request_context())
    
    return jsonify({"error": "An unexpected error occurred"}), 500

@api.errorhandler(404)
def not_found_error_handler(error):
    logger.info("404 - Route not found", extra=helper.get_request_context())
    
    return jsonify({"error": "Resource not found"}), 404

@api.errorhandler(405)
def method_not_allowed(error):
    logger.warning("405 - Method not allowed", extra=helper.get_request_context())
    
    return jsonify({"error": "Method not allowed"}), 405
    
def register_blueprints():
    api.register_blueprint(main, url_prefix="/")
    api.register_blueprint(health, url_prefix="/health")
    api.register_blueprint(auth, url_prefix="/auth")
    api.register_blueprint(users, url_prefix="/users")
    api.register_blueprint(clothing, url_prefix="/clothing")
    api.register_blueprint(static, url_prefix="/static")
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