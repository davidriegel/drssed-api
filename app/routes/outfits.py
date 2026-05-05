from flask import Blueprint, request, jsonify, g
from app.services.outfit import outfit_manager
from app.core.limiter import limiter
from app.utils.middleware.authentication import authorize_request
from app.models.season import Season
from app.models.outfit import OutfitTags
from app.utils.exceptions import ValidationError

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

@outfits.route('/generate', methods=['POST'])
@limiter.limit('10 per minute')
@authorize_request
def generate_outfits():
    data: dict = request.get_json(silent=True) or {}
    
    seasons = data.get("seasons")
    tags = data.get("tags")
    anchor = data.get("anchor")
    amount = data.get("amount", 3)
    typed_seasons = None
    typed_tags = None
    
    if seasons:
        if not isinstance(seasons, list):
            raise ValidationError
        
        for season in seasons:
            if str(season).upper() not in Season.__members__:
                raise ValidationError
        
        typed_seasons = [Season[season.upper()] for season in seasons]
    
    if tags:
        if not isinstance(tags, list):
            raise ValidationError
        
        for tag in tags:
            if str(tag).upper() not in OutfitTags.__members__:
                raise ValidationError
        
        typed_tags = [OutfitTags[tag.upper()] for tag in tags]
        
    if not isinstance(amount, int) or not 1 <= amount <= 10:
        raise ValidationError
    
    if anchor:
        if not isinstance(anchor, list):
            raise ValidationError
        
        for anchor_item in anchor:
            if not isinstance(anchor_item, str):
                raise ValidationError
    
    outfits = outfit_manager.generate_outfit(g.user_id, seasons=typed_seasons, tags=typed_tags, anchor=anchor, amount=amount)
    
    return jsonify({"outfits": [outfit.to_dict() for outfit in outfits], "count": len(outfits)}), 200