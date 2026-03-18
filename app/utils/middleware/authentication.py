__all__ = ["authorize_request"]

from flask import jsonify, request, g
from ..authentication_managment import authentication_manager
from functools import wraps

def authorize_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "No token provided"}), 401

        if not authentication_manager._verify_access_token(token):
            return jsonify({"message": "Unauthorized access"}), 403

        user_id = authentication_manager.get_user_id_from_token(token)

        if not user_id:
            return jsonify({"message": "Unauthorized access"}), 403

        g.user_id = user_id

        return f(*args, **kwargs)

    return wrapper