from flask import Blueprint, request, jsonify, g
from app.utils.clothing_management import clothing_manager
from app.utils.limiter import limiter
from app.utils.middleware.authentication import authorize_request

clothing = Blueprint("clothing", __name__)

@clothing.route('/<clothing_id>', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_clothing_piece(clothing_id: str):
    clothing = clothing_manager.get_clothing_by_id(g.user_id, clothing_id)
    return jsonify(clothing.to_dict()), 200

@clothing.route('/<clothing_id>', methods=['DELETE'])
@limiter.limit('5 per minute')
@authorize_request
def delete_clothing_piece(clothing_id: str):
    clothing_manager.soft_delete_clothing_by_id(g.user_id, clothing_id)

    return "", 204

@clothing.route('/<clothing_id>', methods=['PATCH'])
@limiter.limit('5 per minute')
@authorize_request
def patch_clothing_piece(clothing_id: str):
    token = request.headers["Authorization"]
    data = request.get_json()

    name = data.get("name", None)
    category = data.get("category", None)
    seasons = data.get("seasons", None)
    tags = data.get("tags", None)
    image_id = data.get("image_id", None)
    description = data.get("description", None)
    color = data.get("color", None)
    clothing = clothing_manager.update_clothing(g.user_id, clothing_id, name, category, description, color, seasons, tags, image_id)
    return jsonify({"clothing": clothing.to_dict()}), 200