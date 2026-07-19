import hashlib
import json

from flask import Blueprint, jsonify, request

from app.core.limiter import limiter
from app.models.clothing import ClothingCategory, ClothingSubCategory

taxonomy = Blueprint("taxonomy", __name__)


def _build_taxonomy() -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {
        category.name: [] for category in ClothingCategory
    }
    for sub_category in ClothingSubCategory:
        categories[sub_category.category.name].append(sub_category.name)
    return categories


_TAXONOMY = {"categories": _build_taxonomy()}
_TAXONOMY_ETAG = hashlib.sha256(
    json.dumps(_TAXONOMY, sort_keys=True).encode("utf-8")
).hexdigest()


@taxonomy.route("", methods=["GET"])
@taxonomy.route("/", methods=["GET"])
@limiter.limit("30 per minute")
def get_taxonomy():
    response = jsonify(_TAXONOMY)
    response.set_etag(_TAXONOMY_ETAG)
    response.cache_control.public = True
    response.cache_control.max_age = 3600
    return response.make_conditional(request)
