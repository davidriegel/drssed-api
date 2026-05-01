__all__ = ["authorize_request"]

from flask import request, g
from ..authentication_managment import authentication_manager
from app.utils.exceptions import UnauthorizedError
from functools import wraps

def authorize_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            raise UnauthorizedError

        if not authentication_manager._verify_access_token(token):
            raise UnauthorizedError

        g.user_id = authentication_manager.get_user_id_from_token(token)

        return f(*args, **kwargs)

    return wrapper