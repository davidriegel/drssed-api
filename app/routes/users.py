from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from ..services.user import user_manager
from app.services.outfit import outfit_manager
from app.services.clothing import clothing_manager
from app.models.clothing import ClothingSeason, ClothingTags, ClothingCategory, ClothingSubCategory
from ..utils.exceptions import ValidationError, ConflictError
from ..core.limiter import limiter
from ..utils.helpers import helper
from ..utils.middleware.authentication import authorize_request

users = Blueprint("users", __name__)

@users.route("/me/upgrade", methods=["POST"])
@limiter.limit("5 per minute")
@authorize_request
def upgrade_guest():
    if not g.is_guest:
        raise ConflictError
    
    data: dict = request.get_json()
    
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    profile_picture = data.get("profile_picture")
    
    if not password or not profile_picture or (not email and not username):
        raise ValidationError
    
    user = user_manager.upgrade_guest_account(g.user_id, password, profile_picture, email, username)
    
    return jsonify(user.to_dict()), 201

@users.route("/me/clothing/sync", methods=["GET"])
@limiter.limit('5 per minute')
@authorize_request
def sync_my_clothes():
    updated_since_param = request.args.get("updated_since")

    if updated_since_param:
        try:
            updated_since = datetime.fromisoformat(updated_since_param)
            if updated_since.tzinfo is None:
                updated_since = updated_since.replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "Invalid updated_since timestamp"}), 400
    else:
        updated_since = datetime.fromtimestamp(0, tz=timezone.utc)

    updated_clothes, deleted_clothes_id = clothing_manager.sync_clothes(
        user_id=g.user_id,
        updated_since=updated_since
    )

    return jsonify({
        "updated": [c.to_dict() for c in updated_clothes],
        "deleted": deleted_clothes_id,
        "server_time": datetime.now(timezone.utc).isoformat()
    }), 200

@users.route("/me/outfits/sync", methods=["GET"])
@limiter.limit('5 per minute')
@authorize_request
def sync_my_outfits():
    updated_since_param = request.args.get("updated_since")

    if updated_since_param:
        try:
            updated_since = datetime.fromisoformat(updated_since_param)
            if updated_since.tzinfo is None:
                updated_since = updated_since.replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "Invalid updated_since timestamp"}), 400
    else:
        updated_since = datetime.fromtimestamp(0, tz=timezone.utc)

    updated_outfits, deleted_outfit_ids = outfit_manager.sync_outfits(
        user_id=g.user_id,
        updated_since=updated_since
    )

    return jsonify({
        "updated": [o.to_dict() for o in updated_outfits],
        "deleted": deleted_outfit_ids,
        "server_time": datetime.now(timezone.utc).isoformat()
    }), 200

@users.route('/<user_id>/outfits', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_outfit_list(user_id: str):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    outfit_list, total = outfit_manager.get_list_of_outfits_by_user_id(user_id, limit, offset)

    response = helper.build_paginated_response([o.to_dict() for o in outfit_list], limit, offset, total)
    return jsonify(response), 200

@users.route('/me/outfits', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_outfit_list_private():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    outfit_list, total = outfit_manager.get_list_of_outfits_by_user_id(g.user_id, limit, offset, include_private=True)

    response = helper.build_paginated_response([o.to_dict() for o in outfit_list], limit, offset, total)
    return jsonify(response), 200
    
@users.route('/me/outfits', methods=['POST'])
@limiter.limit('5 per minute')
@authorize_request
def create_outfit():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    outfit = outfit_manager.create_outfit(
        user_id=g.user_id,
        name=data.get("name"),
        description=data.get("description"),
        scene=data.get("scene"),
        seasons=data.get("seasons"),
        tags=data.get("tags"),
        is_public=data.get("is_public"),
        is_favorite=data.get("is_favorite"),
    )

    return jsonify({"outfit": outfit.to_dict()}), 201

@users.route('/<user_id>/clothing', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_clothing_list(user_id: str):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category", None, type=str)

    clothing_list = clothing_manager.get_list_of_clothing_by_user_id(user_id, category, limit, offset)

    return jsonify({"limit": limit, "offset": offset, "clothing": [clothing.to_dict() for clothing in clothing_list]}), 200

@users.route('/me/clothing', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_clothing_list_private():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category", None, type=str)
    
    clothing_list = clothing_manager.get_list_of_clothing_by_user_id(g.user_id, category, limit, offset, include_private=True)
    
    return jsonify({"limit": limit, "offset": offset, "clothing": [clothing.to_dict() for clothing in clothing_list]}), 200
    

@users.route('/me/clothing', methods=['POST'])
@limiter.limit('5 per minute')
@authorize_request
def create_clothing_piece():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get("name", None)
    description = data.get("description", None)
    category = data.get("category", None)
    sub_category = data.get("sub_category", None)
    color = data.get("color", None)
    seasons = data.get("seasons", [])
    tags = data.get("tags", [])
    image_id = data.get("image_id", None)
    
    if not name or not category or not sub_category or not color or not image_id:
        raise ValidationError
    
    if str(category).upper() not in ClothingCategory.__members__:
        raise ValidationError
    
    typed_category = ClothingCategory[category.upper()]
    
    if str(sub_category).upper() not in ClothingSubCategory.__members__:
        raise ValidationError
    
    typed_sub_category = ClothingSubCategory[sub_category.upper()]
    
    for season in seasons:
        if str(season).upper() not in ClothingSeason.__members__:
            raise ValidationError
        
    typed_seasons = [ClothingSeason[season.upper()] for season in seasons]

    for tag in tags:
        if str(tag).upper() not in ClothingTags.__members__:
            raise ValidationError
        
    typed_tags = [ClothingTags[tag.upper()] for tag in tags]

    clothing = clothing_manager.create_clothing(g.user_id, name, typed_category, typed_sub_category, image_id, color, typed_seasons, typed_tags, description)

    return jsonify({"clothing": clothing.to_dict()}), 201

@users.route('/me', methods=['DELETE'])
@limiter.limit('1 per minute')
@authorize_request
def delete_account():
    data = request.get_json()
    if not data:
        raise ValidationError
    
    password = data.get("password")
    if not password:
        raise ValidationError

    user_manager.delete_account_by_id(g.user_id, password)
    
    return jsonify({"message": "Account deleted successfully"}), 200