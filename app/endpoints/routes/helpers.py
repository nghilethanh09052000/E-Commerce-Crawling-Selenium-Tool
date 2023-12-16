from flask_restx import Resource, Namespace
from app import logger
from app.endpoints.validators.driver import get_url_request_parser
from app.helpers.domain_helpers import get_domain_web_stack
from .authenticate import authentication_required

ns = Namespace("helpers", description="Url Helpers", path="/api/helpers")


class BuiltWith(Resource):
    @authentication_required
    @ns.expect(get_url_request_parser, validate=True)
    def post(self):
        """Endpoint to Fetch Domain webstack info"""
        logger.input("Start Get Url BuiltWith Route")

        body = get_url_request_parser.parse_args()
        url = body.url
        url_built_with = get_domain_web_stack(url)
        logger.output(f"Get Url BuiltWith Completed. Response Returned {url_built_with}")
        return url_built_with, 200


ns.add_resource(BuiltWith, "/builtwith", methods=["POST"])
