from flask import Blueprint, request, jsonify, g
from app.utils.outfit_management import outfit_manager
from app.utils.limiter import limiter
from app.utils.middleware.authentication import authorize_request

outfits = Blueprint("outfits", __name__)
    
@outfits.route('/<outfit_id>', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_outfit(outfit_id: str):
    outfit = outfit_manager.get_outfit_by_id(g.user_id, outfit_id)

    return jsonify({"outfit": outfit.to_dict()}), 200

@outfits.route('/<outfit_id>', methods=['DELETE'])
@limiter.limit('5 per minute')
@authorize_request
def delete_outfit(outfit_id: str):
    outfit_manager.soft_delete_outfit_by_id(g.user_id, outfit_id)

    return "", 204

@outfits.route('/<outfit_id>', methods=['PATCH'])
@limiter.limit('3 per minute')
@authorize_request
def patch_outfit(outfit_id: str):
    data: dict = request.get_json()
    
    name = data.get("name")
    is_favorite = data.get("is_favorite")
    is_public = data.get("is_public")
    seasons = data.get("seasons")
    tags = data.get("tags")
    scene = data.get("scene")
    
    outfit = outfit_manager.patch_outfit(g.user_id, outfit_id, name=name, is_favorite=is_favorite, is_public=is_public, seasons=seasons, tags=tags, scene=scene)
    
    return jsonify({"outfit": outfit.to_dict()}), 200