import requests
import os
import json
from multiprocessing import Pool
from time import time
from selenium_driver.search_driver import Selenium
from selenium.webdriver.common.by import By

from navee_utils.domain_helper import get_domain_name_from_url
from app import logger
from app.settings import NAVEE_DRIVER_API_URL, NAVEE_DRIVER_API_TIMEOUT, NAVEE_DRIVER_AUTHORIZATION_KEY, sentry_sdk
from app.helpers.domain_helpers import get_domain_who_is
from app.scrapers.helpers import get_scraper_module
from app.models.enums import ScrapingType, DataSource, UrlPageType, RequestResult, ScrapingActionType
from app.endpoints.service.protobuff_parser import parse_response_to_proto
from app.helpers.utils import (
    download_html_file,
    extract_price_and_currency,
    get_cleaned_post_url,
    get_picutre_selector_from_config,
    reset_config_loading_time,
    url_post_identifiers_retriever_module,
)
from app.service.scrape import scrape
from app.endpoints.service.logger import log_response
from app.helpers.translation import get_text_language, translate_text_into_english
from app.service.scrape_post_info import _get_post_information
from app.configs.utils import load_config
from app.scrapers import InstagramScraper, APIScraper


def get_domain_web_stack(domain_name: str) -> dict():
    """Get Domain Web Stack info"""
    try:
        # builtwith library doesn't have a default timeout so we are using it as an endpoint with inforced timeout
        # Other methods to enforce timeout such as multithreading and signal don't seem to intercept the call hence the use of api
        query = {"url": domain_name}
        headers = {"Content-Type": "application/json", "Authorization": f"{NAVEE_DRIVER_AUTHORIZATION_KEY}"}
        response = requests.post(f"{NAVEE_DRIVER_API_URL}/helpers/builtwith", json=query, headers=headers, timeout=25)
        if response:
            return response.json()
    except Exception as ex:
        print(f"Error on get_domain_web_stack {domain_name} - ex {str(ex)}")

    return None


def parse_url(selenium_driver, item, domain_name):
    """Extract URL Identifier and return cleaned url"""
    url = None
    try:
        url = item.get_attribute("href")
        page_type = get_page_type(selenium_driver, page_url=url, domain_name=domain_name)
        if page_type == UrlPageType.POST:
            post_identifier = selenium_driver.get_post_identifier(
                item, selenium_driver.config.search_pages_browsing_module.post_identifiers_retriever_module
            )
            post_url = selenium_driver.config.post_information_retriever_module.post_url_template.format(
                post_identifier
            )
            return post_url
        # elif page_type == UrlPageType.POSTER:
        #     poster_identifier = selenium_driver.get_post_identifier(
        #         item, selenium_driver.config.search_pages_browsing_module.poster_identifiers_retriever_module
        #     )
        #     poster_url = selenium_driver.config.poster_information_retriever_module.poster_url_template.format(
        #         poster_identifier
        #     )
        #     return poster_url
    except Exception as ex:
        logger.info(f"Error on formatting url {str(ex)}")
    return url


def get_page_type(selenium_driver: Selenium, page_url, domain_name):
    """Try to identify the page type Search/Post/Poster Page"""
    if domain_name == "instagram.com":
        if "/p/" in page_url:
            return UrlPageType.POST
        if "navee_search" in page_url:  # this will be our override key for instagram search
            return UrlPageType.SEARCH

        return UrlPageType.POSTER

    if (
        selenium_driver.config.search_pages_browsing_module
        and selenium_driver.config.search_pages_browsing_module.search_page_urls_builder_module
    ):
        # Check if url falls under search url *
        for (
            search_page_url_template
        ) in (
            selenium_driver.config.search_pages_browsing_module.search_page_urls_builder_module.search_page_url_templates
        ):
            if "{}" in search_page_url_template:
                index = search_page_url_template.index("{")
                search_page_url_template = search_page_url_template[0:index]
            if search_page_url_template != "" and search_page_url_template in page_url:
                return UrlPageType.SEARCH

    if selenium_driver.config.post_information_retriever_module:
        if "{}" in selenium_driver.config.post_information_retriever_module.post_url_template:
            index = selenium_driver.config.post_information_retriever_module.post_url_template.index("{")
            selenium_driver.config.post_information_retriever_module.post_url_template = (
                selenium_driver.config.post_information_retriever_module.post_url_template[0:index]
            )
        if selenium_driver.config.post_information_retriever_module.post_url_template in page_url:
            return UrlPageType.POST

    if (
        selenium_driver.config.poster_information_retriever_module
        and selenium_driver.config.poster_information_retriever_module.poster_url_template != "{}"
    ):
        if "{}" in selenium_driver.config.poster_information_retriever_module.poster_url_template:
            index = selenium_driver.config.poster_information_retriever_module.poster_url_template.index("{")
            selenium_driver.config.poster_information_retriever_module.poster_url_template = (
                selenium_driver.config.poster_information_retriever_module.poster_url_template[0:index]
            )
        if selenium_driver.config.poster_information_retriever_module.poster_url_template in page_url:
            return UrlPageType.POSTER


def get_other_page_links(selenium_driver: Selenium, links_to_exclude, domain_name):
    """Get links available in the page exclude the list"""
    page_links = []
    try:
        links = selenium_driver.driver.wait_and_find_elements(By.TAG_NAME, "a")
        # traverse list
        for link in links:
            url = parse_url(selenium_driver, link, domain_name)
            if url is not None and url not in links_to_exclude:
                page_links.append({"url": url})
                links_to_exclude.append(url)
    except Exception as ex:
        print(str(ex))
        sentry_sdk.capture_exception(str(ex))
    return page_links


def format_page_links(page_links):
    """Default id: {} should change to url :{}"""
    return [page_link_data for key, page_link_data in page_links.items()]


def get_formatted_page_links(domain_name: str, selenium_driver: Selenium, url: str, page_type: str):
    """Scrape Page URLs from Search/Poster Results"""
    scraping_type = None
    max_posts_to_browse = 100
    search_urls = None
    poster_urls = None
    scrape_poster_posts = None
    skip_detailed_post_scraping = None
    scraper_module, source = get_scraper_module(domain_name)
    if domain_name == "instagram.com":
        scraping_type = ScrapingType.POST_SEARCH_COMPLETE
        logger.warn("Url Instagram Scraping not implemented yet")
        return
    elif domain_name == "facebook.com":
        scraping_type = ScrapingType.POST_SEARCH_COMPLETE
        logger.warn("URL Facebook Scraping not implemented yet")
        return
    else:
        skip_detailed_post_scraping = True
        if page_type == UrlPageType.SEARCH:
            scraping_type = ScrapingType.POST_SEARCH_COMPLETE
            search_urls = [url]
        elif page_type == UrlPageType.POSTER:
            scraping_type = ScrapingType.POSTER_SEARCH
            scrape_poster_posts = True
            poster_urls = [url]
        else:
            # Implement information extration here if needed
            return
    light_posts_to_scrape, _, _ = scrape(
        scraper_module=scraper_module,
        domain_name=domain_name,
        scraping_type=scraping_type,
        enable_logging=True,
        max_posts_to_browse=max_posts_to_browse,
        source=source,
        search_urls=search_urls,
        poster_urls=poster_urls,
        scrape_poster_posts=scrape_poster_posts,
        skip_detailed_post_scraping=skip_detailed_post_scraping,
        scrape_search_results=True,
        skip_search_filter=True,
    )
    if light_posts_to_scrape:
        light_posts_to_scrape = format_page_links(light_posts_to_scrape)
    return light_posts_to_scrape


def get_page_links(domain_name: str, selenium_driver: Selenium, url: str, page_type: str):
    """Returns all the href available in the page"""

    page_links = []
    # Get Search results from known format

    formatted_page_links = get_formatted_page_links(
        domain_name=domain_name, page_type=page_type, url=url, selenium_driver=selenium_driver
    )
    if formatted_page_links:
        page_links.extend(formatted_page_links)

    links_to_exclude = [page_link["url"] for page_link in page_links]
    # include links not available in this search results.
    other_page_links = get_other_page_links(selenium_driver, links_to_exclude=links_to_exclude, domain_name=domain_name)
    if other_page_links:
        page_links.extend(other_page_links)

    return page_links


def get_page_data(domain_name: str, selenium_driver: Selenium, url: str, page_type: str, request_params: dict()):
    """Extract Page Data from tracked Websites for Poster/Post Information"""

    scraping_type = None
    max_posts_to_browse = None
    post_urls = []
    poster_urls = []

    # Params related to tasks launched using the API
    scraping_type = ScrapingType[request_params.scraping_type]
    organisation_name = request_params.organisation_name
    send_to_counterfeit_platform = request_params.send_to_counterfeit_platform
    rescrape_existing_posts = request_params.rescrape_existing_posts
    source = DataSource[request_params.source]
    enable_logging = request_params.enable_logging

    # upload related fields
    upload_post = request_params.upload_post
    upload_request_id = request_params.upload_request_id
    upload_id = request_params.upload_id
    post_identifier_url_mapping = None
    post_identifier_upload_id_mapping = None
    scraper_module, _ = get_scraper_module(domain_name)
    if domain_name == "instagram.com":
        logger.warn("Url Instagram Scraping not implemented yet")
        return
    else:
        if page_type == UrlPageType.POST:
            scraping_type = ScrapingType.POST_SCRAPE_FROM_LIST
            post_identifier = url_post_identifiers_retriever_module(
                url,
                selenium_driver.config.search_pages_browsing_module.post_identifiers_retriever_module,
            )
            post_urls.append(post_identifier)

            if upload_id:
                upload_post[0]["post_identifier"] = post_identifier

                post_identifier_url_mapping = {post_identifier: url}
                # Build a mapping post_identifier_upload_id_mapping: post_identifier -> upload_id
                post_identifier_upload_id_mapping = {post_identifier: upload_id}

        elif page_type == UrlPageType.POSTER:
            if domain_name == "facebook.com":
                logger.warn("Url Facebook Scraping not implemented yet")
                return

            scraping_type = ScrapingType.POSTER_SEARCH
            ### TODO: Implement Poster ID Retrieval
            # poster_identifier = url_post_identifiers_retriever_module(
            #     url,
            #     selenium_driver.config.search_pages_browsing_module.poster_identifiers_retriever_module,
            # )
            poster_urls.append(url)
        else:
            # Implement information extration here if needed
            return

    _, scraped_posts, scraped_posters = scrape(
        scraper_module=scraper_module,
        domain_name=domain_name,
        search_queries=None,
        organisation_name=organisation_name,
        send_to_counterfeit_platform=send_to_counterfeit_platform,
        scraping_type=scraping_type,
        enable_logging=enable_logging,
        max_posts_to_browse=max_posts_to_browse,
        rescrape_existing_posts=rescrape_existing_posts,
        post_urls=post_urls,
        poster_urls=poster_urls,
        source=DataSource(source),
        scrape_search_results=True,
        skip_search_filter=True,
        upload_request_id=upload_request_id,
        upload_posts_batch=None if upload_post is None else upload_post,
        post_identifier_url_mapping=post_identifier_url_mapping,
        post_identifier_upload_id_mapping=post_identifier_upload_id_mapping,
    )
    if page_type == UrlPageType.POST:
        if not scraped_posts:
            return
        scraped_posts[0]["type"] = UrlPageType.POST.name
        return scraped_posts[0]
    elif page_type == UrlPageType.POSTER:
        if not scraped_posters:
            return
        # to be replaced once field type is unified accross Insta/Marketplace
        scraped_posters = list(scraped_posters) if type == dict else scraped_posters
        scraped_posters[0]["type"] = UrlPageType.POSTER.name
        return scraped_posters[0]
    return None


def get_who_is_information(domain_name: str) -> dict():
    """Get Domain Who is Information"""
    try:
        domain_info = {}
        domain_info["who_is_information"] = get_domain_who_is(domain_name)
        return domain_info
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Error getting who is information for {domain_name}: {e}")


def get_web_stack_information(domain_name: str) -> dict():
    """Get Built with stack"""
    try:
        domain_info = {}
        domain_info["web_stack_information"] = get_domain_web_stack(domain_name)
        return domain_info
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Error getting web stack information for {domain_name}: {e}")


def clean_url(url: str):
    """Default url cleaning to remove irrelevant query strings"""
    ## remove any Navee keys from query string
    args = []
    ## remove common query string known to have no impact on the url

    return url, args


def get_page_information(domain_name: str, url: str, request_params: dict()) -> dict():
    """Main Function to Get all Page Information Available"""
    start_time = time()
    domain_for_driver = domain_name
    if request_params.action_type == ScrapingActionType.ARCHIVING.name:
        domain_for_driver = None
    selenium_driver = Selenium(domain_for_driver)
    ## TODO: Clean the url
    # url , **args = clean_url(url)
    page_info = {}
    page_type = request_params.page_type
    if not page_type:
        page_type = get_page_type(selenium_driver, page_url=url, domain_name=domain_name)
    else:
        page_type = UrlPageType[page_type]

    # Scrape Information
    if request_params.action_type != ScrapingActionType.ARCHIVING.name:
        page_data = get_page_data(
            domain_name=domain_name,
            page_type=page_type,
            url=url,
            selenium_driver=selenium_driver,
            request_params=request_params,
        )
        ## update real value of url after cleaning
        if page_data:
            page_info["data"] = page_data
            if "url" in page_data:
                page_info["url"] = page_data["url"]
                url = page_data["url"]
        else:
            return page_info
    time_spend = time() - start_time
    if time_spend > NAVEE_DRIVER_API_TIMEOUT / 3:
        logger.warn(
            f"Interrupted due to slow scraping ({int(time_spend)} seconds), extend_page_info() was not called for {url}"
        )
        return page_info
    try:
        extend_page_info(page_info, selenium_driver, domain_name, page_type, url)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Error getting extend_page_info for {url}: {repr(e)}")

    selenium_driver.kill_driver()
    return page_info


def extend_page_info(page_info, selenium_driver, domain_name, page_type, url):
    if not selenium_driver.get(url):
        return

    page_info["s3_content_url"] = selenium_driver.get_page_source()

    page_info["outgoing_links"] = get_page_links(
        domain_name=domain_name, page_type=page_type, url=url, selenium_driver=selenium_driver
    )
    page_info["title"] = selenium_driver.get_page_title()
    page_info["description"] = selenium_driver.get_page_metadata(specific_key="description")

    # Translate information
    if page_info["title"] is not None:
        translated_title = translate_text_into_english(page_info["title"])
        if translated_title != page_info["title"]:
            page_info["translated_title"] = translated_title

    if page_info["description"] is not None:
        translated_description = translate_text_into_english(page_info["description"])
        # default language en to know that translation was applied
        page_info["source_language"] = "en"
        if translated_description != page_info["description"]:
            page_info["translated_description"] = translated_description
            source_language = get_text_language(page_info["description"])
            if source_language is not None:
                page_info["source_language"] = source_language

    if page_info.get("data", None) is not None and page_info["data"].get("archive_link", None) is not None:
        page_info["s3_archive_url"] = page_info["data"]["archive_link"]
    else:
        scraping_attempt = selenium_driver.get(url)
        if scraping_attempt.request_result != RequestResult.SUCCESS:
            return

        webshot = selenium_driver.take_webshot()
        if webshot is not None:
            page_info["s3_archive_url"] = webshot


def get_url(url, request_params):
    """main function to get url and all corresponding metada that can be scraped"""
    ## # TODO:
    # Disect url to check who is the domain name
    # If we know the domain name try parsing the url
    # Try to get information within the post

    # If we don't load selenium and return response
    logger.info(f"Launching Selenium to Retrieve Data for Url {url}")

    response = {
        "url": url,
    }

    domain_name = get_domain_name_from_url(url)
    logger.info(f"Get Url Completed for Url {url}")

    # run each function in a different process
    successful = True
    with Pool() as pool:
        page_information = pool.apply_async(
            get_page_information,
            args=(domain_name, url, request_params),
        )
        who_is_information = pool.apply_async(get_who_is_information, args=(domain_name,))
        web_stack_information = pool.apply_async(get_web_stack_information, args=(domain_name,))

        for i, info in enumerate((page_information, who_is_information, web_stack_information)):
            try:
                # TODO: Propogate status and error from scraper
                page_information_result = info.get(timeout=NAVEE_DRIVER_API_TIMEOUT - 2)
            except Exception as e:
                message = f"Error during getting info {repr(e)}"
                logger.error(message)
                response.setdefault("errors", []).append(message)
                page_information_result = None
            if page_information_result is None:
                if i == 0:
                    successful = False
                continue
            if "errors" in page_information_result:
                response.setdefault("errors", []).extend(page_information_result.get("errors"))
                del page_information_result["errors"]
            response.update(page_information_result)
    response["successful"] = successful

    # Parse Response to protobuff
    scraping_result, scraping_result_json = parse_response_to_proto(response)

    # Log Response
    log_response(url, scraping_result)

    logger.info(f"Return Information Retrieved for url {url}")
    return json.loads(scraping_result_json)


def get_post_from_api(domain_name, scraper_module, post_url, config):
    post_information = {}
    if domain_name == "instagram.com":
        if "/p/" in post_url:
            post_identifier = post_url.split("/p/")[1].split("/")[0]
        else:
            return post_information
    else:
        post_identifier = url_post_identifiers_retriever_module(
            post_url,
            config.search_pages_browsing_module.post_identifiers_retriever_module,
        )
        if not post_identifier:
            # unable to retrieve identifier to scrape
            return post_information

    _, scraped_posts, _ = scrape(
        scraper_module=scraper_module,
        domain_name=domain_name,
        send_to_counterfeit_platform=False,
        post_urls=[post_identifier],
        scraping_type=ScrapingType.POST_SCRAPE_FROM_LIST,
        rescrape_existing_posts=True,
        enable_logging=True,
        scrape_search_results=True,
    )

    # Cater for different response types in different Scrapers
    if domain_name == "instagram.com":
        scraped_posts = format_page_links(scraped_posts)
        post_information.update(
            {
                "url": scraped_posts[0].get("url"),
                "description": scraped_posts[0].get("caption"),
                "vendor": scraped_posts[0].get("owner", None).get("username"),
            }
        )
    else:
        if scraped_posts and scraped_posts[0]:
            post_information.update(
                {
                    "url": scraped_posts[0].get("url"),
                    "title": scraped_posts[0].get("title"),
                    "price": scraped_posts[0].get("price"),
                    "description": scraped_posts[0].get("description"),
                    "images": scraped_posts[0].get("pictures"),
                    "vendor": scraped_posts[0].get("vendor"),
                    "poster_link": scraped_posts[0].get("poster_link"),
                }
            )
            if post_information["price"]:
                post_information["price"], post_information["currency_code"] = extract_price_and_currency(
                    post_information["price"]
                )
        else:
            # nothing was scraped
            return post_information
    return post_information


def get_offline_post(post_url, html_s3_url, domain_name):
    ## Get Post Information from download HTML Content
    config = load_config(domain_name)
    scraper_module, _ = get_scraper_module(domain_name)
    post_identifier, post_url = get_cleaned_post_url(post_url, config)

    # scrape API Providers from their scraper module
    try:
        if scraper_module in (InstagramScraper, APIScraper):
            return get_post_from_api(domain_name, scraper_module, post_url, config)
        else:
            return get_post_from_html(post_url, html_s3_url, domain_name, config, post_identifier)
    except Exception as ex:
        logger.error(f"error scraping offling post {str(ex)}")
    return {}


def get_post_from_html(post_url, html_s3_url, domain_name, config, post_identifier):
    post_information = {"url": post_url}
    # download file
    html_file_path = download_html_file(html_s3_url)
    if html_file_path is None:
        logger.info(f"Error downloading {html_file_path}")
    else:
        try:
            # change config loading delays for 0 as its an offline scraping of a loaded page
            config = reset_config_loading_time(config)
            ## add config to load selenium offline
            config.proxies = None
            config.driver_initialization_module.load_offline_driver = True
            config.driver_initialization_module.undetected_driver = False
            config.post_information_retriever_module.take_screenshot = False
            logger.info(f"Download HTML {html_s3_url} - Path {html_file_path}")
            selenium_driver = Selenium(domain_name=domain_name, config=config)
            # get the url
            selenium_driver.get(f"file://{html_file_path}", offline_driver=True)
            post_information.update(
                _get_post_information(
                    post_identifier=post_identifier, selenium_driver=selenium_driver, post_url=post_url, config=config
                )
            )
            if post_information["pictures"]:
                post_information["images"] = post_information["pictures"]

            if post_information["price"]:
                post_information["price"], post_information["currency_code"] = extract_price_and_currency(
                    post_information["price"]
                )
            selenium_driver.kill_driver()
        except Exception as ex:
            logger.error(f"Error on offline scraping {str(ex)}")

    if html_file_path:
        os.remove(html_file_path)

    # for pictures share the selectors to use
    post_information["pictures"] = get_picutre_selector_from_config(config)
    return post_information
