from flask import Blueprint, g, jsonify, request

from app.core.limiter import limiter
from app.services.clothing import clothing_manager
from app.utils.middleware.authentication import authorize_request

clothing = Blueprint("clothing", __name__)


@clothing.route("/<clothing_id>", methods=["GET"])
@limiter.limit("5 per minute")
@authorize_request
def get_clothing_piece(clothing_id: str):
    clothing = clothing_manager.get_clothing_by_id(g.user_id, clothing_id)
    return jsonify(clothing.to_dict()), 200


@clothing.route("/<clothing_id>", methods=["DELETE"])
@limiter.limit("5 per minute")
@authorize_request
def delete_clothing_piece(clothing_id: str):
    clothing_manager.soft_delete_clothing_by_id(g.user_id, clothing_id)

    return "", 204


@clothing.route("/<clothing_id>", methods=["PATCH"])
@limiter.limit("5 per minute")
@authorize_request
def patch_clothing_piece(clothing_id: str):
    request.headers["Authorization"]
    data = request.get_json()

    name = data.get("name", None)
    sub_category = data.get("sub_category", None)
    seasons = data.get("seasons", None)
    tags = data.get("tags", None)
    image_id = data.get("image_id", None)
    color = data.get("color", None)
    warmth_level = data.get("warmth_level", None)
    clothing = clothing_manager.update_clothing(
        g.user_id,
        clothing_id,
        name,
        sub_category,
        color,
        warmth_level,
        seasons,
        tags,
        image_id,
    )
    return jsonify({"clothing": clothing.to_dict()}), 200
