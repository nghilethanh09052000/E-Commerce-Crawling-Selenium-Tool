import os
from flask import Flask, url_for
from flask_restx import Api
from werkzeug.exceptions import HTTPException

# Compilation of functions that need to be run at the start of the progra
from navee_utils import app_base

from navee_logging import NaveeLogger, NaveeModule

from app.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    ENVIRONMENT_NAME,
    sentry_sdk,
    SWAGGER_SCHEME,
)

# We need to initialize the logger before loading the app models
logger = NaveeLogger(
    NaveeModule.SPECIFIC_SCRAPER,
    aws_access_key=AWS_ACCESS_KEY_ID,
    aws_secret_key=AWS_SECRET_ACCESS_KEY,
    aws_region=AWS_REGION,
    environment=ENVIRONMENT_NAME,
    dev=(ENVIRONMENT_NAME == "development"),
)


# Swagger with HTTPS
@property
def specs_url(self):
    """Fixes issue where swagger-ui makes a call to swagger.json over HTTP.
    This can ONLY be used on servers that actually use HTTPS.  On servers that use HTTP,
    this code should not be used at all.
    """
    return url_for(self.endpoint("specs"), _external=True, _scheme=SWAGGER_SCHEME)


def create_app():
    app = Flask(__name__)

    # Prevent flask restplus from overriding response when 404 (fixed in latest version of flask restplus)
    app.config["ERROR_404_HELP"] = False

    # Prevent flask restplus from returning an additional message field on error's response
    app.config["ERROR_INCLUDE_MESSAGE"] = False

    app.config["SAML_PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saml_settings")

    # Add security headers
    # security.init_app(app, force_https=False, strict_transport_security=True, content_security_policy=csp)
    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = "default-source' ''self'; object-src' ''none'; img-src * "
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Server"] = "-"
        response.headers["Etag"] = "-"

        return response

    from app.endpoints.routes import driver_ns, helpers_ns, health_check_ns

    from app.endpoints.validators.driver import ns as models_drivers_ns

    # disable documentation on production environment
    doc = False if ENVIRONMENT_NAME == "production" else "/api/"

    # Use HTTPS on staging environment
    if ENVIRONMENT_NAME == "staging":
        Api.specs_url = specs_url

    api = Api(app, version="2.0", endpoint="/api/", doc=doc)
    api.add_namespace(driver_ns)
    api.add_namespace(helpers_ns)
    api.add_namespace(health_check_ns)

    # validation models
    api.add_namespace(models_drivers_ns)

    @api.errorhandler  # for v2 apis
    @app.errorhandler(HTTPException)  # for v1 apis
    def default_error_handler(error):
        """Default error handler"""
        sentry_sdk.capture_exception(error)
        err_msg = getattr(error, "description", str(error))

        try:
            err_code = int(getattr(error, "code", 500)) if getattr(error, "code", 500) else 500
        except ValueError:
            err_code = 500

        return {"error message": err_msg if err_msg else "unexpected server-side error"}, err_code

    # Force flask restplus to use default_error_handler() (open issue when using debug mode)
    api._default_error_handler = Exception
    api.error_handlers[Exception] = default_error_handler

    return app, api


app, api = create_app()
