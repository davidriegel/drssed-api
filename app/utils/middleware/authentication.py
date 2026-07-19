__all__ = ["authorize_request"]

from functools import wraps

from flask import g, request

from app.utils.exceptions import UnauthorizedError

from ...services.authentication import authentication_manager


def authorize_request(f):
    """Authorizes Bearer Token and sets g.user_id, g.is_guest to requesting users account status"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")

        if token and token.startswith("Bearer "):
            token = token[7:]
        else:
            token = None

        if not token:
            raise UnauthorizedError

        g.user_id = authentication_manager.get_user_id_from_token(token)
        g.is_guest = authentication_manager.get_is_guest_from_token(token)

        return f(*args, **kwargs)

    return wrapper
