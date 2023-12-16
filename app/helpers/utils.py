from io import BytesIO
import json
import os
from uuid import uuid4
import magic
import re
import string

from PIL import Image, UnidentifiedImageError
import pillow_avif  # noqa - do not delete: require to load avif images
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from app import logger, sentry_sdk
from app.configs.utils import load_config
from app.models.marshmallow.config import ScrapeSchema


def merge_dict_values(*dicts):
    """Add Dicts Values {'a':1} {'a':3} --> {'a':4}"""
    res = dict()
    for d in dicts:
        for k, v in d.items():
            if type(v) == int:
                res[k] = res.get(k, 0) + v
    return res


def remove_localization(url, localisation_country_list):
    """For domains that have country codes in path that have no impact on content.

    Example: product/uk/item.html --> /product/item.html
    """

    url_parts = url.split("/")

    for url_part in url_parts:
        if url_part.lower() in localisation_country_list:
            url = url.replace(f"/{url_part}", "")

    return url


def extract_url_from_string(url, config):
    """
    Extract URL contained inside a parameter of a post URL
    Example: https://www.example.com/some_path?some_key=URL_TO_EXTRACT

    url_parameter (required): Key value of URL parameter to extract
    extract_if_match_regex (required): Extract URL only if input URL matches regex.
    """

    url_parameter = config.url_parameter
    extract_if_match_regex = config.extract_if_match_regex

    if re.search(extract_if_match_regex, url):
        # Parse input URL
        parsed_url_string = urlparse(url)
        # Extract value from parameter
        extracted_url = parse_qs(parsed_url_string.query)[url_parameter][0]
        return extracted_url

    return url


def get_cleaned_post_url(url, config):
    try:
        post_identifier = url_post_identifiers_retriever_module(
            url,
            config.search_pages_browsing_module.post_identifiers_retriever_module,
        )
        if post_identifier:
            return post_identifier, config.post_information_retriever_module.post_url_template.format(post_identifier)
    except Exception as ex:
        logger.error(f"Error cleaning url {url} {str(ex)}")
        sentry_sdk.capture_exception(ex)
    return None, url


def clean_url(url, config):
    """Clean the URL from unecessary text in the path that varies for the same post url. This will resolve duplicate post issue"""

    # Remove unnecessary query string with post url
    try:
        query_string_to_keep = config.query_string_to_keep if config else None
        localisation_country_list = config.localisation_country_list if config else None
        skip_query_string_cleaning = config.skip_query_string_cleaning if config else None
        extract_url_from_string_parameter = config.extract_url_from_string_parameter if config else None

        if extract_url_from_string_parameter is not None:
            url = extract_url_from_string(url, extract_url_from_string_parameter)

        if skip_query_string_cleaning:
            return url

        query_string_to_add = {}

        if query_string_to_keep:
            parsed_url = urlparse(url)
            query_strings_in_url = parse_qs(parsed_url.query)

            if len(query_strings_in_url) > 0:
                for entry in query_string_to_keep:
                    if entry in query_strings_in_url:
                        query_string_to_add[entry] = query_strings_in_url[entry][0]

        # remove any data past # to avoid duplication of post
        url = url.split("#")[0]

        # remove any query strings to avoid duplication of post
        url = url.split("?")[0]

        if len(query_string_to_add) > 0:
            url = f"{url}?{urlencode(query_string_to_add)}"

        if localisation_country_list:
            url = remove_localization(url, localisation_country_list)

        # Remove any ending / in urls
        if url[-1] == "/":
            url = url[:-1]

        # if config.regex_substitute:
        #     url = re.sub(config.regex_substitute, "", url)

    except Exception as ex:
        logger.info(f"Exception on clean_url : {str(ex)}")
        return url

    return url


def chunks(lst, n):
    """Yield successive n-sized chunks from lst"""

    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def load_instagram_search_configs():
    with open("app/configs/instagram/instagram_search_configs.json", "r") as f:
        instagram_search_configs = json.load(f)

    return instagram_search_configs


def url_post_identifiers_retriever_module(url, config):
    """Return the post identifier for a given url"""

    url = clean_url(url, config.post_url_cleaning_module)
    regex = config.regex

    if regex and re.search(regex, url):
        url = re.search(regex, url).group(1)

    return url


def get_post_identifiers(domain_name, posts):
    config = load_config(domain_name)

    for post in posts:
        post["post_identifier"] = url_post_identifiers_retriever_module(
            post["url"] if "post" not in post else post["post"]["url"],
            config.search_pages_browsing_module.post_identifiers_retriever_module,
        )

    post_identifiers = [post["post_identifier"] for post in posts if post["post_identifier"]]
    post_identifiers = dict.fromkeys(post_identifiers)

    return post_identifiers, posts


def guess_image_mime_type(img_bytes):
    mime_type = magic.from_buffer(img_bytes, mime=True)
    if mime_type.startswith("image"):
        return mime_type
    try:
        mime_type = Image.open(BytesIO(img_bytes)).get_format_mimetype()
    except UnidentifiedImageError:
        return False
    if mime_type.startswith("image"):
        return mime_type
    return False


def reset_config_loading_time(config):
    fields = ["loading_time", "loading_timeout", "loading_delay", "after_pause_time", "before_pause_time"]
    schema = ScrapeSchema()
    obj = schema.dump(config)
    update_dict_fields(obj, fields, 0)
    return schema.load(obj)


def update_dict_fields(obj, fields, new_value):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in fields:
                obj[key] = new_value
            elif isinstance(value, (dict, list)):
                update_dict_fields(value, fields, new_value)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                update_dict_fields(item, fields, new_value)
    return obj


def get_picutre_selector_from_config(config):
    if config.post_information_retriever_module and config.post_information_retriever_module.pictures_retriever_module:
        return {
            "clickable_css_selector_1": config.post_information_retriever_module.pictures_retriever_module.clickable_css_selector_1,
            "clickable_css_selector_2": config.post_information_retriever_module.pictures_retriever_module.clickable_css_selector_2,
            "picture_css_selector": config.post_information_retriever_module.pictures_retriever_module.picture_css_selector,
            "attribute_name": config.post_information_retriever_module.pictures_retriever_module.attribute_name,
        }


def download_html_file(link):
    try:
        file_name = f"{uuid4()}_webshot.html"
        response = requests.get(link)
        response.raise_for_status()  # Raise an exception if the request was not successful

        with open(file_name, "wb") as file:
            file.write(response.content)

        return os.path.abspath(file_name)

    except Exception as ex:
        logger.error(f"Error downloading file {str(ex)}")
        sentry_sdk.capture_exception(ex)
    return None


def extract_price_and_currency(text):
    # Pattern to match the price and currency
    currency = None
    price = None
    currency_match = re.search(r"[A-Za-z]{3}", text)
    price_match = re.search(r"[\d,\.]+", text)
    if currency_match:
        currency = currency_match.group()
    if price_match:
        price = price_match.group()
    return price, currency


def get_search_query_by_urls(config, queries, max_posts_to_discover=None, template_name="search_page_url_templates"):
    """Return the list of search URLs"""

    search_query_by_urls = {}
    for search_query in queries:
        for search_page_url_template in getattr(config.search_page_urls_builder_module, template_name):
            field_names = [v[1] for v in string.Formatter().parse(search_page_url_template)]
            search_url = (
                search_page_url_template.format(SEARCH_QUERY=search_query)
                if "SEARCH_QUERY" in field_names
                else search_page_url_template.format(search_query)
            )
            search_url = (
                search_url.replace("MAX_POSTS_TO_BROWSE", str(max_posts_to_discover))
                if "MAX_POSTS_TO_BROWSE" in search_url
                else search_url
            )

            search_query_by_urls[search_url] = search_query

    return search_query_by_urls


def get_formatted_post_body(post_body, query, max_posts_to_discover):
    """Return API request post body with search queries and max results"""

    if post_body:
        if "SEARCH_QUERY" in post_body:
            post_body = post_body.replace("SEARCH_QUERY", query)
        if "MAX_POSTS_TO_BROWSE" in post_body:
            post_body = post_body.replace("MAX_POSTS_TO_BROWSE", str(max_posts_to_discover))

    return post_body
