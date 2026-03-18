from flask import Blueprint, request, jsonify, g
from app.utils.clothing_managment import clothing_manager
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
    clothing_manager.delete_clothing_by_id(g.user_id, clothing_id)

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

"""
@clothing.route('/<clothingID>', methods=['PUT'])
@limiter.limit('5 per minute')
@authorize_request
def updateClothing(clothingID: str):
    token = request.headers["Authorization"]
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        name = data.get("name")
        description = data.get("description")
        category = data.get("category")
        color = data.get("color")
        seasons = data.get("seasons")
        tags = data.get("tags")
        image_url = data.get("image")
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
    if not any([name, description, category, color, seasons, tags, image_url]):
        return jsonify({"error": "No data provided"}), 400
    
    if name:
        name = str(name).strip()
        
    if description:
        description = str(description).strip()
        
    if color:
        color = str(color).strip()
        colorRegex = r"^#([A-Fa-f0-9]{6})$"
        if not re.match(colorRegex, color):
            return jsonify({"error": "The provided color is not valid"}), 400
        
    if category:
        category = str(category).upper()
        if category not in ClothingCategory.__members__:
            return jsonify({"error": "The provided category is not valid."}), 400
        
        category = ClothingCategory[category].name
    
    seasonsList = None
    if seasons is not None:
        seasons: list[str] = seasons
        for season in seasons:
            if str(season).capitalize() not in ["Spring", "Summer", "Autumn", "Winter"]:
                return jsonify({"error": f"The provided season ({season}) is not valid."}), 400
            
        seasonsList = [season.capitalize() for season in seasons]
    
    tagsList = None
    if tags is not None:
        tags: list[str] = tags
        for tag in tags:
            if tag.capitalize() not in ["Casual", "Formal", "Sports", "Vintage"]:
                return jsonify({"error": f"The provided tag ({tag}) is not valid."}), 400
            
        tagsList = [tag.capitalize() for tag in tags]
    
    try:
        clothing = clothing_manager.updateClothing(token, clothingID, name, category, description, color, seasonsList, tagsList, image_url)
    except ClothingNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except (ClothingNameTooShortError, ClothingNameTooLongError, ClothingDescriptionTooLongError) as e:
        return jsonify({"error": str(e)}), 400
    
    return jsonify(clothing.to_dict()), 200
    """