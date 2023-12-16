from flask import request
from functools import wraps
from werkzeug.exceptions import Unauthorized
from app.settings import NAVEE_DRIVER_AUTHORIZATION_KEY


def authentication_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None
        # ensure the jwt-token is passed with the headers
        if "Authorization" in request.headers:
            token = request.headers["Authorization"]
        if not token:  # throw error if no token provided
            raise Unauthorized("A valid token is missing!")
        if NAVEE_DRIVER_AUTHORIZATION_KEY == token:
            return f(*args, **kwargs)
        else:
            raise Unauthorized("Invalid token!")

    return decorator
