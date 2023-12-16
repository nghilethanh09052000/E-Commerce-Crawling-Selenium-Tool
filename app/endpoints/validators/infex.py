from flask_restx import Namespace, reqparse

ns = Namespace("infex")

get_infex_request_parser = reqparse.RequestParser()

get_infex_request_parser.add_argument("page_url", type=str, required=True, help="page URL to scrape", location="json")
get_infex_request_parser.add_argument("image_url", type=str, required=True, help="image URL to scrape", location="json")
get_infex_request_parser.add_argument("image_s3_url", type=str, required=False, default=None, location="json")
get_infex_request_parser.add_argument("recursion", type=int, required=False, default=0, location="json")
get_infex_request_parser.add_argument("scroll_smoothly", type=bool, required=False, default=False, location="json")
get_infex_request_parser.add_argument("js_postprocess", type=bool, required=False, default=False, location="json")
get_infex_request_parser.add_argument("remove_invisible_boxes", type=bool, required=False, default=True, location="json")
get_infex_request_parser.add_argument("other_xpaths", type=dict, required=False, default={}, location="json")
get_infex_request_parser.add_argument("page_timeout_override", type=int, required=False, default=None, location="json")
get_infex_request_parser.add_argument("element_timeout_override", type=int, required=False, default=None, location="json")
