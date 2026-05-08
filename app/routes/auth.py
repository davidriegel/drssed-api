from flask import Blueprint, request, jsonify, g, render_template
from app.services.authentication import authentication_manager
from app.utils.middleware.authentication import authorize_request
from app.services.user import user_manager
from app.core.limiter import limiter
from app.utils.exceptions import ValidationError, NotFoundError

auth = Blueprint("auth", __name__)

@auth.route('/email/send-verification', methods=['POST'])
@authorize_request
@limiter.limit("3 per hour", key_func=lambda: str(g.user_id))
def email_verification():
    authentication_manager.create_email_verification(g.user_id, g.preferred_language)
    return {}, 200

@auth.route('/email/verify', methods=['GET'])
@limiter.limit('60 per minute')
def verify_email():
    token = request.args.get("token")
    
    if not token:
        return render_template(f'/verification/email_verified.{g.preferred_language}.html', status='invalid'), 400
    
    try:
        verified_email = authentication_manager.verify_email(token)
        return render_template(f'/verification/email_verified.{g.preferred_language}.html', status='success', email=verified_email), 200
    except NotFoundError:
        return render_template(f'/verification/email_verified.{g.preferred_language}.html', status='invalid'), 400

@auth.route('/guest', methods=['POST'])
@limiter.limit('1 per hour')
def register_guest():
    token = authentication_manager.register_guest(preferred_language=g.preferred_language)
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
def delete_refresh_token():
    data = request.get_json()
    refresh_token = data.get("refresh_token")
    
    if not refresh_token:
        raise ValidationError

    authentication_manager.delete_refresh_token(refresh_token)

    return jsonify({}), 204
    
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