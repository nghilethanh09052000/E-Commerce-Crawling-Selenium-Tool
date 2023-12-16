from flask_restx import Namespace, Resource

from app import logger
from app.endpoints.service.taobao_cookies import retrieve_cookies
from app.endpoints.service.driver import get_offline_post, get_url
from app.endpoints.validators.driver import get_url_request_parser, get_post_response_model
from app.endpoints.validators.infex import get_infex_request_parser
from eb_infex_worker.information_extraction.main import infex_single_website

from .authenticate import authentication_required

ns = Namespace("driver", description="Driver Endpoint to process request", path="/api/driver")


class Driver(Resource):
    @authentication_required
    @ns.expect(get_url_request_parser, validate=True)
    def post(self):
        """Fetch url information"""
        logger.input("Start Get Url Route")

        body = get_url_request_parser.parse_args()
        logger.info(f"received body: {body}")
        url = body.url
        url_data = get_url(url, body)
        logger.output(f"Get Url Route Completed. Response Returned {url_data}")
        return url_data, 200


ns.add_resource(Driver, "", methods=["POST"])


class DriverTaobaoCookies(Resource):
    @authentication_required
    def get(self):
        logger.input("Start retrieving Taobao cookies")
        cookie = retrieve_cookies()
        logger.output(f"Cookies retrieved. Response Returned {cookie}")

        return cookie, 200


ns.add_resource(DriverTaobaoCookies, "/taobao_cookies", methods=["GET"])


class DriverInfex(Resource):
    @ns.expect(get_infex_request_parser, validate=True)
    @authentication_required
    def post(self):
        logger.input("Start retrieving infex page")

        body = get_infex_request_parser.parse_args()

        (extracted_page_url, title, price, description, poster, pattern_detected, infex_error) = infex_single_website(
            body.page_url,
            body.image_url,
            body.image_s3_url,
            body.recursion,
            body.scroll_smoothly,
            body.js_postprocess,
            body.remove_invisible_boxes,
            body.other_xpaths,
            body.page_timeout_override,
            body.element_timeout_override,
        )

        response = {
            "extracted_page_url": extracted_page_url,
            "title": title,
            "price": price,
            "description": description,
            "poster": poster,
            "pattern_detected": pattern_detected,
            "infex_error": infex_error,
        }

        logger.output(f"Infex page retrieved. Returns {response}")

        return response, 200


ns.add_resource(DriverInfex, "/infex", methods=["POST"])


class ScrapeOfflinePost(Resource):
    @authentication_required
    @ns.expect(get_url_request_parser, validate=True)
    @ns.marshal_with(get_post_response_model)
    def post(self):
        """Fetch url information"""
        logger.input("Start Scraping Offline Post")

        body = get_url_request_parser.parse_args()
        url = body.url
        html_s3_url = body.html_s3_url
        domain_name = body.domain_name

        url_data = get_offline_post(url, html_s3_url, domain_name)
        logger.output(f"Scraping Offline Post Completed. Response Returned {url_data}")
        return url_data, 200


ns.add_resource(ScrapeOfflinePost, "/post", methods=["POST"])
