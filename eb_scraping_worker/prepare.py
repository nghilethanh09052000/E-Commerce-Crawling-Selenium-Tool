from enum import Enum
from pprint import pprint

from navee_utils.domain_helper import get_domain_name_from_url
from app.configs.utils import load_config
from app.helpers.utils import url_post_identifiers_retriever_module
from app.models.enums import DataSource, ScrapingType, UrlPageType
from app.scrapers.helpers import get_scraper_module

SCRAPING_DEFAULTS = {
    "enable_logging": True,
    "organisation_name": "Test_Organisation_QA",
    "rescrape_existing_posts": True,
    "scrape_search_results": True,
    "screenshot_posts": True,
    "screenshot_profiles": True,
    "send_to_counterfeit_platform": True,
    "skip_search_filter": True,
    "source": DataSource.SPECIFIC_SCRAPER,
    "concurrency": 1,
}


def prepare_scraping_params(worker_input):
    scraping_params = dict()

    url = worker_input.get("url")
    domain_name = worker_input.get("domain_name")
    if not domain_name:
        if url:
            domain_name = get_domain_name_from_url(url)
        elif website_id := worker_input.get("website_id"):
            raise AssertionError(f"website_id usage is not implemented ({website_id})")
        else:
            raise AssertionError("Cannot determine domain")
    assert domain_name, "Cannot determine domain_name"
    worker_input["domain_name"] = domain_name
    scraping_params["domain_name"] = domain_name

    domain_config = load_config(domain_name, load_chrome_profile=False)
    scraper_module, _ = get_scraper_module(domain_name, config=domain_config)
    scraping_params["scraper_module"] = scraper_module

    page_type = worker_input.get("page_type")
    if page_type == UrlPageType.POST.name:
        type_specific_params = prepare_post_params(worker_input, domain_config)
    elif page_type == UrlPageType.POSTER.name:
        type_specific_params = prepare_poster_params(worker_input, domain_config)
    elif page_type is None:
        raise AssertionError("mandatory field 'page_type' is not specified in the worker_input")
    else:
        raise AssertionError(
            f"unsupported page_type '{page_type}' (only {UrlPageType.POSTER.name} and {UrlPageType.POSTER.name} are allowed)"
        )
    scraping_params.update(type_specific_params)

    for k, v in SCRAPING_DEFAULTS.items():
        if isinstance(v, Enum) and k in worker_input:
            try:
                scraping_params[k] = type(v)[worker_input.get(k)]
            except KeyError as e:
                raise AssertionError(f"invalid value for '{k}': there is no {str(e)} in {str(type(v))} ")
        else:
            scraping_params[k] = worker_input.get(k, v)

    known_keys = set(scraping_params) | {
        "url",
        "page_type",
        "post_identifier",
        "upload_id",
        "tags",
        "label",
        "username",
    }
    for k, v in worker_input.items():
        if k not in known_keys:
            scraping_params[k] = v

    return scraping_params


def prepare_poster_params(worker_input, domain_config):
    scraping_params = dict()
    scraping_params["scraping_type"] = ScrapingType.POSTER_SEARCH
    scraping_params["scrape_poster_posts"] = False
    scraping_params["rescrape_existing_profiles"] = True

    url = worker_input.get("url")
    domain_name = worker_input["domain_name"]

    if domain_name == "instagram.com":
        scraping_params["skip_search_filter"] = True
        username = worker_input.get("username") or extract_username_instagram(url)
        assert username, f"Cannot extract username from {url} (domain_name: {domain_name})"
        scraping_params["usernames"] = [username]
        scraping_params["upload_account_identifier_url_mapping"] = {username: url}
    else:
        assert url, "worker_input missing mandatory field for POSTER: 'url'"
        scraping_params["poster_urls"] = {url: None}
        if upload_id := worker_input.get("upload_id"):
            scraping_params["upload_account_identifier_url_mapping"] = {url: upload_id}

    upload_accounts_batch = [worker_input]
    scraping_params["upload_accounts_batch"] = upload_accounts_batch

    return scraping_params


def extract_username_instagram(url):
    if url is None:
        return None
    try:
        return url.split("instagram.com/")[1].split("/")[0]
    except IndexError:
        return None


def prepare_post_params(worker_input, domain_config):
    scraping_params = dict()
    scraping_params["scraping_type"] = ScrapingType.POST_SCRAPE_FROM_LIST

    url = worker_input.get("url")
    post_identifier = worker_input.get("post_identifier")
    domain_name = worker_input["domain_name"]
    if not url:
        assert (
            post_identifier
            and domain_config
            and domain_config.post_information_retriever_module
            and domain_config.post_information_retriever_module.post_url_template
        ), f"Cannot make url from {post_identifier} (post_url_template is not specified for domain_name: {domain_name})"
        url = domain_config.post_information_retriever_module.post_url_template.format(post_identifier)
        worker_input["url"] = url

    if not post_identifier:
        if domain_name == "instagram.com":
            assert "/p/" in url, f"Invalit url format for instagram: {url}"
            post_identifier = url.split("/p/")[1].split("/")[0]
        else:
            assert (
                url
                and domain_config
                and domain_config.search_pages_browsing_module
                and domain_config.search_pages_browsing_module.post_identifiers_retriever_module
            ), f"Cannot extract post_identifier from {url} (post_identifiers_retriever_module is not specified for domain_name: {domain_name})"
            post_identifier = url_post_identifiers_retriever_module(
                url,
                domain_config.search_pages_browsing_module.post_identifiers_retriever_module,
            )
    assert post_identifier, f"post_identifier is not found in url: {url} (domain_name: {domain_name})"
    worker_input["post_identifier"] = post_identifier
    post_urls = [post_identifier]
    scraping_params["post_urls"] = post_urls

    post_identifier_url_mapping = {post_identifier: url}
    scraping_params["post_identifier_url_mapping"] = post_identifier_url_mapping

    upload_posts_batch = [worker_input]
    scraping_params["upload_posts_batch"] = upload_posts_batch

    upload_id = worker_input.get("upload_id")
    if upload_id:
        post_identifier_upload_id_mapping = {post_identifier: upload_id}
        scraping_params["post_identifier_upload_id_mapping"] = post_identifier_upload_id_mapping
    return scraping_params


if __name__ == "__main__":

    url = "https://www.instagram.com/p/CvfMX_qtsyy/"

    worker_input = {
        # mandatory
        "url": url,
        "page_type": "POST",
        #
        # alternative for POST: (domain_name or website_id) + post_identifier
        # "domain_name": "redbubble.com",
        # "website_id": 97,
        # "post_identifier": "sticker/Three-Sexy-Waifus-in-Lingerie-by-IdaSloan/151694021.EJUG5",
        #
        # meaningful optional
        # "organisation_name": "Chanel_Navee",
        # "upload_id": 999,  # to upd upload_history table
        # "upload_request_id": "tttsss",  # (with upload_id) to upd ss_redis
        # "tags": ["test_tag"],
        # "label": "Counterfeit",
        # "source": "MANUAL_INSERTION"
    }

    print("\nworker_input:")
    pprint(worker_input)
    scraping_params = prepare_scraping_params(worker_input)
    print("\nscraping_params:")
    pprint(scraping_params)
