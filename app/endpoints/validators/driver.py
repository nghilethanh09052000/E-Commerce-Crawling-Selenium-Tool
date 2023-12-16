from flask_restx import Namespace, reqparse, inputs, fields

from app.models.enums import ScrapingType, DataSource, ScrapingActionType

ns = Namespace("driver", description="Driver related response model")

get_url_request_parser = reqparse.RequestParser()
get_url_request_parser.add_argument("url", type=str, required=True, help="URL to Scrape", location="json")
get_url_request_parser.add_argument(
    "html_s3_url", type=str, required=False, help="html_s3_url to Scrape", location="json"
)
get_url_request_parser.add_argument(
    "domain_name", type=str, required=False, help="domain_name to Scrape", location="json"
)
# Addditional fields to enable using the endpoint for cronjobs
get_url_request_parser.add_argument(
    "scraping_type",
    default=str(ScrapingType.POST_SCRAPE_FROM_LIST.name),
    type=str,
    required=False,
    help="Scraping Type",
    location="json",
)
get_url_request_parser.add_argument(
    "page_type",
    default=None,
    type=str,
    required=False,
    help="Page Type",
    location="json",
)
get_url_request_parser.add_argument(
    "organisation_name",
    default=None,
    type=str,
    required=False,
    help="Name of the organisation requesting",
    location="json",
)
get_url_request_parser.add_argument(
    "send_to_counterfeit_platform",
    default=False,
    type=inputs.boolean,
    required=False,
    help="Should automatically send post to organisation ?",
    location="json",
)
get_url_request_parser.add_argument(
    "rescrape_existing_posts",
    default=False,
    type=inputs.boolean,
    required=False,
    help="Rescrape Post if non existing",
    location="json",
)
get_url_request_parser.add_argument(
    "source",
    default=DataSource.SPECIFIC_SCRAPER.name,
    type=str,
    required=False,
    help="source of scraping request",
    location="json",
)
get_url_request_parser.add_argument(
    "upload_request_id",
    default=None,
    type=str,
    required=False,
    help="The upload Request ID for uploads",
    location="json",
)
get_url_request_parser.add_argument(
    "upload_id",
    default=None,
    type=str,
    required=False,
    help="The upload ids in upload",
    location="json",
)
get_url_request_parser.add_argument(
    "enable_logging",
    default=True,
    type=str,
    required=False,
    help="Should automatically enable logging",
    location="json",
)
get_url_request_parser.add_argument(
    "upload_post",
    default=None,
    type=dict,
    action="append",
    required=False,
    help="Upload Related Batching",
    location="json",
)
get_url_request_parser.add_argument(
    "just_return_html_content",
    default=False,
    type=inputs.boolean,
    required=False,
    help="Just return the raw HTML content of the page",
    location="json",
)
get_url_request_parser.add_argument(
    "action_type",
    default=ScrapingActionType.SCRAPING.name,
    type=str,
    required=False,
    help="action type for scraping ",
    location="json",
)


picture_selector_model = ns.model(
    "PictureSelector",
    {
        "clickable_css_selector_1": fields.String(required=True, description="Clickable CSS Selector 1"),
        "clickable_css_selector_2": fields.String(required=True, description="Clickable CSS Selector 2"),
        "picture_css_selector": fields.String(required=True, description="Image Selector"),
        "attribute_name": fields.String(required=True, description="Atrribute name"),
        "regex": fields.String(required=True, description="Regex"),
    },
)

picture_model = ns.model(
    "Picutre",
    {
        "s3_url": fields.String(required=True, description="S3 URL"),
        "picture_url": fields.String(required=True, description="Image URL"),
    },
)

get_post_response_model = ns.model(
    "GetPostResponse",
    {
        "title": fields.String(required=True, description="Title of the post"),
        "description": fields.String(required=True, description="Description of the post"),
        "url": fields.String(required=True, description="URL of the post"),
        "price": fields.String(required=True, description="Price of the post"),
        "currency_code": fields.String(required=True, description="Price of the post"),
        "vendor": fields.String(required=True, description="Vendor of the post"),
        "pictures": fields.Nested(picture_selector_model, required=True, description="Picture Selector of the post"),
        "images": fields.List(fields.Nested(picture_model, required=True, description="Images of the post")),
    },
)
