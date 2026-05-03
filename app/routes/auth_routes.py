from flask import Blueprint, request, jsonify, g
from app.utils.authentication_managment import authentication_manager
from app.utils.middleware.authentication import authorize_request
from app.utils.user_managment import user_manager
from app.utils.limiter import limiter
from app.utils.exceptions import ValidationError

auth = Blueprint("auth", __name__)


@auth.route('/guest', methods=['POST'])
@limiter.limit('5 per hour')
def register_guest():
    token = authentication_manager.register_guest()
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)

    return jsonify(token.to_dict()), 201

@auth.route('/refresh', methods=['POST'])
@limiter.limit('5 per minute')
def refresh_access_token():
    data = request.get_json()
    
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise ValidationError

    token = authentication_manager.refresh_access_token(refresh_token)
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)

    return jsonify(token.to_dict()), 200

@auth.route('/logout', methods=['POST'])
@limiter.limit('2 per minute')
@authorize_request
def delete_refresh_token():
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise ValidationError

    authentication_manager.delete_refresh_token(refresh_token)

    return "", 204
    
@auth.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data: dict = request.get_json()
    
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    
    if not password or (not email and not username):
        raise ValidationError
    
    token = authentication_manager.sign_in_user(email, username, password)
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)
    
    return jsonify(token.to_dict())