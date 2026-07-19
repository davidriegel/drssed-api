from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request
from flask.typing import ResponseReturnValue

from app.models.clothing import ClothingCategory, ClothingSubCategory, ClothingTags
from app.models.season import Season
from app.services.authentication import authentication_manager
from app.services.clothing import clothing_manager
from app.services.outfit import outfit_manager

from ..core.limiter import limiter
from ..services.user import user_manager
from ..utils.exceptions import ConflictError, ValidationError
from ..utils.helpers import helper
from ..utils.middleware.authentication import authorize_request

users = Blueprint("users", __name__)


@users.route("/me/upgrade", methods=["POST"])
@limiter.limit("5 per minute")
@authorize_request
def upgrade_guest() -> ResponseReturnValue:
    if not g.is_guest:
        raise ConflictError

    data: dict = request.get_json()

    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    profile_picture = data.get("profile_picture")

    if not password or not profile_picture or (not email and not username):
        raise ValidationError

    user = user_manager.upgrade_guest_account(
        g.user_id, password, profile_picture, email, username
    )

    authentication_manager.revoke_all_refresh_tokens(g.user_id)

    new_tokens = authentication_manager.sign_in_user(email, username, password)

    return jsonify(
        {
            "user": user.model_dump(mode="json"),
            "token": new_tokens.model_dump(mode="json"),
        }
    ), 201


@users.route("/me/clothing/sync", methods=["GET"])
@limiter.limit("5 per minute")
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
        user_id=g.user_id, updated_since=updated_since
    )

    return jsonify(
        {
            "updated": [c.to_dict() for c in updated_clothes],
            "deleted": deleted_clothes_id,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    ), 200


@users.route("/me/outfits/sync", methods=["GET"])
@limiter.limit("5 per minute")
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
        user_id=g.user_id, updated_since=updated_since
    )

    return jsonify(
        {
            "updated": [o.to_dict() for o in updated_outfits],
            "deleted": deleted_outfit_ids,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    ), 200


@users.route("/<user_id>/outfits", methods=["GET"])
@limiter.limit("5 per minute")
@authorize_request
def get_outfit_list(user_id: str):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    outfit_list, total = outfit_manager.get_list_of_outfits_by_user_id(
        user_id, limit, offset
    )

    response = helper.build_paginated_response(
        [o.to_dict() for o in outfit_list], limit, offset, total
    )
    return jsonify(response), 200


@users.route("/me/outfits", methods=["GET"])
@limiter.limit("5 per minute")
@authorize_request
def get_outfit_list_private():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    outfit_list, total = outfit_manager.get_list_of_outfits_by_user_id(
        g.user_id, limit, offset, include_private=True
    )

    response = helper.build_paginated_response(
        [o.to_dict() for o in outfit_list], limit, offset, total
    )
    return jsonify(response), 200


@users.route("/me/outfits", methods=["POST"])
@limiter.limit("5 per minute")
@authorize_request
def create_outfit():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    outfit = outfit_manager.create_outfit(
        user_id=g.user_id,
        name=data.get("name"),
        scene=data.get("scene"),
        seasons=data.get("seasons"),
        tags=data.get("tags"),
        is_public=data.get("is_public"),
        is_favorite=data.get("is_favorite"),
    )

    return jsonify({"outfit": outfit.to_dict()}), 201


@users.route("/<user_id>/clothing", methods=["GET"])
@limiter.limit("5 per minute")
@authorize_request
def get_clothing_list(user_id: str):
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category", None, type=str)

    typed_category: ClothingCategory | None = None

    if category:
        if category not in ClothingCategory.__members__:
            raise ValidationError

        typed_category = ClothingCategory[category]

    clothing_list = clothing_manager.get_list_of_clothing_by_user_id(
        user_id, category=typed_category, limit=limit, offset=offset
    )

    return jsonify(
        {
            "limit": limit,
            "offset": offset,
            "clothing": [clothing.to_dict() for clothing in clothing_list],
        }
    ), 200


@users.route("/me/clothing", methods=["GET"])
@limiter.limit("5 per minute")
@authorize_request
def get_clothing_list_private() -> ResponseReturnValue:
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    category = request.args.get("category", None, type=str)

    typed_category: ClothingCategory | None = None

    if category:
        if category not in ClothingCategory.__members__:
            raise ValidationError

        typed_category = ClothingCategory(category)

    clothing_list = clothing_manager.get_list_of_clothing_by_user_id(
        g.user_id,
        category=typed_category,
        limit=limit,
        offset=offset,
        only_public=False,
    )

    return jsonify(
        {
            "limit": limit,
            "offset": offset,
            "clothing": [clothing.to_dict() for clothing in clothing_list],
        }
    ), 200


@users.route("/me/clothing", methods=["POST"])
@limiter.limit("5 per minute")
@authorize_request
def create_clothing_piece():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get("name", None)
    sub_category = data.get("sub_category", None)
    color = data.get("color", None)
    warmth_level = data.get("warmth_level", None)
    seasons = data.get("seasons", [])
    tags = data.get("tags", [])
    image_id = data.get("image_id", None)

    if (
        not name
        or not sub_category
        or not color
        or not image_id
        or warmth_level is None
    ):
        raise ValidationError

    if str(sub_category).upper() not in ClothingSubCategory.__members__:
        raise ValidationError

    typed_sub_category = ClothingSubCategory[sub_category.upper()]

    for season in seasons:
        if str(season).upper() not in Season.__members__:
            raise ValidationError

    typed_seasons = [Season[season.upper()] for season in seasons]

    for tag in tags:
        if str(tag).upper() not in ClothingTags.__members__:
            raise ValidationError

    typed_tags = [ClothingTags[tag.upper()] for tag in tags]

    clothing = clothing_manager.create_clothing(
        g.user_id,
        name,
        typed_sub_category,
        image_id,
        color,
        warmth_level,
        typed_seasons,
        typed_tags,
    )

    return jsonify({"clothing": clothing.to_dict()}), 201


@users.route("/me/password", methods=["PATCH"])
@authorize_request
@limiter.limit("5 per minute", key_func=lambda: str(g.user_id))
def change_password() -> ResponseReturnValue:
    if g.is_guest:
        raise ConflictError

    data: dict = request.get_json() or {}

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        raise ValidationError

    token = authentication_manager.change_password(
        g.user_id, current_password, new_password
    )

    return jsonify({"token": token.model_dump(mode="json")}), 200


@users.route("/me/email", methods=["PATCH"])
@authorize_request
@limiter.limit("3 per hour", key_func=lambda: str(g.user_id))
def change_email() -> ResponseReturnValue:
    if g.is_guest:
        raise ConflictError

    data: dict = request.get_json() or {}

    current_password = data.get("current_password")
    new_email = data.get("new_email")

    if not current_password or not new_email:
        raise ValidationError

    pending_email = authentication_manager.request_email_change(
        g.user_id, current_password, new_email, g.preferred_language
    )

    return jsonify({"pending_email": pending_email}), 202


@users.route("/me", methods=["DELETE"])
@limiter.limit("1 per minute")
@authorize_request
def delete_account():
    user_manager.delete_account_by_id(g.user_id)

    return jsonify({}), 204


@users.route("/me", methods=["GET"])
@authorize_request
@limiter.limit("3 per minute")
def get_current_user():
    user = user_manager.get_private_user_profile_by_id(g.user_id)
    return jsonify({"user": user.model_dump(mode="json")}), 200
