from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from ..utils.user_managment import user_manager
from app.utils.outfit_managment import outfit_manager
from app.utils.clothing_managment import clothing_manager
from ..utils.exceptions import UsernameTooShortError, UsernameTooLongError, UsernameAlreadyInUseError, UserNotFoundError, UnsupportedFileTypeError
from ..utils.limiter import limiter
from ..utils.helpers import helper
from ..utils.authentication_managment import authorize_request

users = Blueprint("users", __name__)

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
    limit = request.args.get("limit", 1000, type=int)
    offset = request.args.get("offset", 0, type=int)

    outfit_list, total = outfit_manager.get_list_of_outfits_by_user_id(user_id, limit, offset)

    response = helper.build_paginated_response([o.to_dict() for o in outfit_list], limit, offset, total)
    return jsonify(response), 200

@users.route('/me/outfits', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_outfit_list_private():
    limit = request.args.get("limit", 1000, type=int)
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
    limit = request.args.get("limit", 1000, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category", None, type=str)

    clothing_list = clothing_manager.get_list_of_clothing_by_user_id(user_id, category, limit, offset)

    return jsonify({"limit": limit, "offset": offset, "clothing": [clothing.to_dict() for clothing in clothing_list]}), 200

@users.route('/me/clothing', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def get_clothing_list_private():
    limit = request.args.get("limit", 1000, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category", None, type=str)
    
    clothing_list = clothing_manager.get_list_of_clothing_by_user_id(g.user_id, category, limit, offset, include_private=True)
    
    return jsonify({"limit": limit, "offset": offset, "clothing": [clothing.to_dict() for clothing in clothing_list]}), 200
    

@users.route('/me/clothing', methods=['POST'])
@limiter.limit('5 per minute')
@authorize_request
def create_clothing_piece():
    token = request.headers["Authorization"]
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    name = data.get("name", None)
    description = data.get("description", None)
    category = data.get("category", None)
    color = data.get("color", None)
    seasons = data.get("seasons", [])
    tags = data.get("tags", [])
    image_id = data.get("image_id", None)

    clothing = clothing_manager.create_clothing(g.user_id, name, category, image_id, color, seasons, tags, description)

    return jsonify({"clothing": clothing.to_dict()}), 201

@users.route('/me/username', methods=['PUT'])
@authorize_request
@limiter.limit('1 per hour')
def set_new_username():
    data: dict = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    username = data.get("username", None)
    
    try:
        user_manager.update_user_username(g.user_id, username)
    except (UsernameTooShortError, UsernameTooLongError) as e:
        return jsonify({"error": str(e)}), 400
    except UsernameAlreadyInUseError as e:
        return jsonify({"error": str(e), "key": "username"}), 409
    
    return jsonify({"message": "Username updated successfully."}), 200

"""
@users.route('/me', methods=['GET'])
@limiter.limit('10 per minute')
@authorize_request
def getMyUser():
    token = request.headers["Authorization"]
    
    user = user_manager.getMyUser(token)
    
    return jsonify(user.__dict__), 200

@users.route('/<userid>', methods=['GET'])
@limiter.limit('10 per minute')
@authorize_request
def getUserByUserID(userid: str):
    try:
        user = user_manager.getUserByUserID(userid)
    except UserNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    
    return jsonify(user.__dict__), 200

@users.route('/<userid>/profilepicture', methods=['GET'])
@limiter.limit('5 per minute')
@authorize_request
def getUserProfilePicture(userid: str):
    try:
        profilePictureURL = user_manager.getUserProfilePicture(userid)
    except UserNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    
    return jsonify({"path": f"{str(profilePictureURL)}"}), 200


@users.route('/me/profilepicture', methods=['PUT', 'GET', 'DELETE'])
@limiter.limit('5 per minute')
@authorize_request
def userProfilePicture():
    token = request.headers["Authorization"]
    
    if request.method == 'GET':
        return getMyUserProfilePicture(token)
    elif request.method == 'PUT':
        return setMyUserProfilePicture(token)
    else:
        return deleteMyUserProfilePicture()
        
def setMyUserProfilePicture(token: str) -> Response:
    if "file" not in request.files:
        profilePicture = request.args.get("named")
        
        if not profilePicture:
            return jsonify({"error": "No file provided"}), 400
        
        if not profilePicture.endswith(".png"):
            profilePicture += ".png"
        
        #try:
        #    user = user_manager.setDefaultProfilePicture(profilePicture, token)
        #except UserProfilePictureNotFoundError as e:
        #    return jsonify({"error": str(e)}), 404
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
        
    if len(file.read()) > 2*1024*1024:
        return jsonify({"error": "File is too large (max 2MB)"}), 400
    
    file.seek(0)
    
    try:
        user = user_manager.setProfilePicture(file, token)
    except UnsupportedFileTypeError as e:
        return jsonify({"error": str(e)}), 400
    
    return jsonify(user.__dict__), 200

def getMyUserProfilePicture(token: str) -> Response:
    profilePictureURL = user_manager.getMyProfilePicture(token)
    
    return jsonify({"path": f"{str(profilePictureURL)}"}), 200

def deleteMyUserProfilePicture(token: str):
    #try:
    #    user_manager.removeProfilePicture(token)
    #except UserProfilePictureNotFoundError as e:
    #    return jsonify({"error": str(e)}), 404
    
    return jsonify({"message": "Profile picture deleted successfully"}), 200
"""

# TODO: Create endpoint to delete account