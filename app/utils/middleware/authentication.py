__all__ = ["authorize_request"]

from flask import request, g
from ...services.authentication import authentication_manager
from app.utils.exceptions import UnauthorizedError
from functools import wraps

def authorize_request(f):
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