from functools import wraps

from jsonschema import validate

from .schemas import (followers_schema, post_schema, posts_schema,  # noqa:F401
                      profile_details_schema)


def validate_output(schema):

    def decorator(f):
        @wraps(f)
        def wrapping(*args, **kwargs):
            output = f(*args, **kwargs)
            validate(output, schema)
            return output
        return wrapping

    return decorator
