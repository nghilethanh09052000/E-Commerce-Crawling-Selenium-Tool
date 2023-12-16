import os
import yaml
import re
from urllib.parse import parse_qs, urlencode, urlparse
from typing import Dict, Optional

import hiyapyco

from app.models import Post
from .marshmallow.config import ScrapeSchema
from automated_moderation.utils.logger import log

configs = {}


def load_domain_config(config_file) -> Optional[ScrapeSchema]:
    try:
        if config_file == "ymatou.hk":
            config_file = "ymatou.com"

        if not os.path.isfile(f"automated_moderation/specific_scraper/config/{config_file}.yaml"):
            log.warn(f"Unable to find {config_file} yaml file")
            return

        with open(f"automated_moderation/specific_scraper/config/{config_file}.yaml", "r") as yamlfile:

            config = yaml.load(yamlfile, Loader=yaml.FullLoader)

            # Include inheritance to main .yaml file
            filename_to_include = config.get("include", None)

            if filename_to_include:

                config = hiyapyco.load(
                    f"automated_moderation/specific_scraper/config/{config_file}.yaml",
                    f"automated_moderation/specific_scraper/config/{filename_to_include}",
                    method=hiyapyco.METHOD_MERGE,
                    usedefaultyamlloader=True,
                )

            return ScrapeSchema().load(config["framework"])
    except Exception as ex:
        log.error(f"Exception on load_domain_config : {repr(ex)}")
        return


def get_post_platform_id(post: Post) -> Dict[str, Post]:
    if not (config := configs.get(post.website.domain_name, load_domain_config(post.website.domain_name))):
        return {}

    if not config.search_pages_browsing_module:
        return {}

    post_platform_id = url_post_identifiers_retriever_module(
        post.link, config.search_pages_browsing_module.post_identifiers_retriever_module
    )

    return {post_platform_id: post}


def url_post_identifiers_retriever_module(url, config):
    """Return the post identifier for a given url"""

    url = clean_url(url, config.post_url_cleaning_module)
    regex = config.regex

    if regex and re.search(regex, url):
        url = re.search(regex, url).group(1)

    return url


def clean_url(url, config):
    """Clean the URL from unecessary text in the path that varies for the same post url. This will resolve duplicate post issue"""

    # Remove unnecessary query string with post url
    try:
        query_string_to_keep = config.query_string_to_keep if config else None
        localisation_country_list = config.localisation_country_list if config else None
        skip_query_string_cleaning = config.skip_query_string_cleaning if config else None

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
        log.info(f"Exception on clean_url : {str(ex)}")
        return url

    return url


def remove_localization(url, localisation_country_list):
    """For domains that have country codes in path that have no impact on content.

    Example: product/uk/item.html --> /product/item.html
    """

    url_parts = url.split("/")

    for url_part in url_parts:
        if url_part.lower() in localisation_country_list:
            url = url.replace(f"/{url_part}", "")

    return url
