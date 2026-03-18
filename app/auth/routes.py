from flask import Blueprint, request, jsonify, g
#from app.utils.exceptions import EmailInvalidError, PasswordTooShortError, UsernameTooLongError, UsernameTooShortError, EmailAlreadyInUseError, WrongSignInCredentialsError, UsernameAlreadyInUseError, AuthValidationError, UserProfilePictureNotFoundError
from app.utils.authentication_managment import authentication_manager
from app.utils.middleware.authentication import authorize_request
from app.utils.user_managment import user_manager
from app.utils.limiter import limiter

auth = Blueprint("auth", __name__)


@auth.route('/guest', methods=['POST'])
@limiter.limit('5 per hour')
def register_guest():
    access_token, expires_in, refresh_token = authentication_manager.register_guest()

    return jsonify({"access_token": access_token, "expires_in": expires_in, "refresh_token": refresh_token}), 201

@auth.route('/refresh', methods=['POST'])
@limiter.limit('5 per minute')
def refresh_access_token():
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    access_token = data.get("access_token")

    access_token, expires_in, refresh_token = authentication_manager.refresh_access_token(access_token, refresh_token)

    return jsonify({"access_token": access_token, "expires_in": expires_in, "refresh_token": refresh_token}), 200

@auth.route('/signout', methods=['POST'])
@limiter.limit('2 per minute')
@authorize_request
def delete_refresh_token():
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    authentication_manager.delete_refresh_token(refresh_token)

    return "", 204

@auth.route("/upgrade", methods=["POST"])
@limiter.limit("5 per minute")
@authorize_request
def upgrade_guest():
    data: dict = request.get_json()
    
    email = data.get("email", None)
    username = data.get("username", None)
    password = data.get("password", None)
    profile_picture = data.get("profile_picture", None)
    
    user = user_manager.upgrade_guest_account(g.user_id, email, username, password, profile_picture)
    
    return jsonify(user.from_dict), 201
    
@auth.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data: dict = request.get_json()
    
    email = data.get("email", None)
    username = data.get("username", None)
    password = data.get("password", None)
    
    access_token, expires_in, refresh_token = authentication_manager.sign_in_user(email, username, password)
    
    return jsonify({"access_token": access_token, "expires_in": expires_in, "refresh_token": refresh_token})