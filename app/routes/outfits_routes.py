from flask import Blueprint, request, jsonify
from app.utils.outfit_managment import outfit_manager
from app.utils.limiter import limiter
from app.utils.middleware.authentication import authorize_request

outfits = Blueprint("outfits", __name__)
    
@outfits.route('/<outfit_id>', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_outfit(outfit_id: str):
    token = request.headers["Authorization"]
    outfit = outfit_manager.get_outfit_by_id(outfit_id, token)

    return jsonify({"outfit": outfit.to_dict()}), 200

@outfits.route('/<outfit_id>', methods=['DELETE'])
@limiter.limit('5 per minute')
@authorize_request
def delete_outfit(outfit_id: str):
    token = request.headers["Authorization"]
    outfit_manager.delete_outfit_by_id(token, outfit_id)

    return "", 204