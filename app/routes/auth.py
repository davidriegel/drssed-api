from flask import Blueprint, g, jsonify, render_template, request
from flask.typing import ResponseReturnValue

from app.core.limiter import limiter
from app.services.authentication import authentication_manager
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.middleware.authentication import authorize_request

auth = Blueprint("auth", __name__)


@auth.route("/email/send-verification", methods=["POST"])
@authorize_request
@limiter.limit("3 per hour", key_func=lambda: str(g.user_id))
def email_verification():
    authentication_manager.create_email_verification(g.user_id, g.preferred_language)
    return {}, 200


@auth.route("/email/verify", methods=["GET"])
@limiter.limit("60 per minute")
def verify_email():
    token = request.args.get("token")

    if not token:
        return render_template(
            f"/verification/email_verified.{g.preferred_language}.html",
            status="invalid",
        ), 400

    try:
        verified_email = authentication_manager.verify_email(token)
        return render_template(
            f"/verification/email_verified.{g.preferred_language}.html",
            status="success",
            email=verified_email,
        ), 200
    except NotFoundError:
        return render_template(
            f"/verification/email_verified.{g.preferred_language}.html",
            status="invalid",
        ), 400


@auth.route("/password/forgot", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    data: dict = request.get_json() or {}

    email = data.get("email")

    if not email:
        raise ValidationError

    authentication_manager.request_password_reset(email, g.preferred_language)

    return {}, 202


@auth.route("/password/reset", methods=["GET"])
@limiter.limit("60 per minute")
def reset_password_form():
    token = request.args.get("token")

    if not token or not authentication_manager.is_password_reset_token_valid(token):
        return render_template(
            f"/password_reset/new_password.{g.preferred_language}.html",
            status="invalid",
        ), 400

    return render_template(
        f"/password_reset/new_password.{g.preferred_language}.html",
        status="form",
        token=token,
    ), 200


@auth.route("/password/reset", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    token = request.form.get("token")
    new_password = request.form.get("new_password")
    confirmed_password = request.form.get("confirmed_password")

    if not token:
        return render_template(
            f"/password_reset/new_password.{g.preferred_language}.html",
            status="invalid",
        ), 400

    if not new_password or new_password != confirmed_password:
        return render_template(
            f"/password_reset/new_password.{g.preferred_language}.html",
            status="form",
            token=token,
            error="mismatch",
        ), 400

    try:
        authentication_manager.reset_password(token, new_password)
    except ValidationError:
        return render_template(
            f"/password_reset/new_password.{g.preferred_language}.html",
            status="form",
            token=token,
            error="too_short",
        ), 400
    except NotFoundError:
        return render_template(
            f"/password_reset/new_password.{g.preferred_language}.html",
            status="invalid",
        ), 400

    return render_template(
        f"/password_reset/new_password.{g.preferred_language}.html",
        status="success",
    ), 200


@auth.route("/guest", methods=["POST"])
@limiter.limit("10 per hour")
def register_guest():
    token = authentication_manager.register_guest(
        preferred_language=g.preferred_language
    )
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)

    return jsonify(token.model_dump(mode="json")), 201


@auth.route("/refresh", methods=["POST"])
@limiter.limit("5 per minute")
def refresh_access_token():
    data = request.get_json()

    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise ValidationError

    token = authentication_manager.refresh_access_token(refresh_token)
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)

    return jsonify(token.model_dump(mode="json")), 200


@auth.route("/logout", methods=["POST"])
@limiter.limit("2 per minute")
def delete_refresh_token():
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        raise ValidationError

    authentication_manager.delete_refresh_token(refresh_token)

    return jsonify({}), 204


@auth.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login() -> ResponseReturnValue:
    data: dict = request.get_json()

    email = data.get("email")
    username = data.get("username")
    password = data.get("password")

    if not password or (not email and not username):
        raise ValidationError

    token = authentication_manager.sign_in_user(email, username, password)
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)

    return jsonify(token.model_dump(mode="json")), 200


@auth.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register_user() -> ResponseReturnValue:
    data: dict = request.get_json()

    email = data.get("email")
    username = data.get("username")
    password = data.get("password")
    profile_picture = data.get("profile_picture")

    if not password or not profile_picture or (not email and not username):
        raise ValidationError

    token = authentication_manager.register_user(
        email, username, password, profile_picture=profile_picture
    )
    g.user_id = authentication_manager.get_user_id_from_token(token.access_token)

    return jsonify(token.model_dump(mode="json")), 201
