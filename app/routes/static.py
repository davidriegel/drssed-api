from flask import Blueprint, jsonify, send_from_directory
from werkzeug.exceptions import NotFound

from app.core.limiter import limiter
from app.utils.middleware.authentication import authorize_request

static = Blueprint("static", __name__)


@static.route("/clothing_images/<clothing_id>.webp", methods=["GET"])
@static.route("/clothing_images/<clothing_id>", methods=["GET"])
@limiter.limit("10 per minute")
@authorize_request
def getClothingImage(clothing_id):
    try:
        return send_from_directory("app/static/clothing_images", f"{clothing_id}.webp")
    except NotFound:
        return jsonify({"error": "File not found."}), 404


@static.route("/temp/<filename>", methods=["GET"])
@limiter.limit("2 per minute")
@authorize_request
def getTempImage(filename):
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    filename = (
        filename.strip() + ".webp" if not filename.endswith(".webp") else filename
    )

    try:
        return send_from_directory("app/static/temp", f"{filename}")
    except NotFound:
        return jsonify({"error": "File not found."}), 404


@static.route("/outfit_images/<filename>", methods=["GET"])
@limiter.limit("10 per minute")
@authorize_request
def get_outfit_image(filename):
    filename = (
        filename.strip() + ".webp" if not filename.endswith(".webp") else filename
    )

    try:
        return send_from_directory("app/static/outfit_collages", f"{filename}")
    except NotFound:
        return jsonify({"error": "File not found."}), 404


@static.route("/profile_pictures/<filename>", methods=["GET"])
@limiter.limit("60 per minute")
@authorize_request
def get_profile_picture(filename):
    filename = (
        filename.strip() + ".webp" if not filename.endswith(".webp") else filename
    )

    try:
        return send_from_directory("app/static/profile_pictures", f"{filename}")
    except NotFound:
        return jsonify({"error": "File not found."}), 404
