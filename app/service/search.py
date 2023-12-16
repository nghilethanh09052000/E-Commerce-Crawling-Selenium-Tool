from datetime import datetime, timedelta
from typing import Optional, List, Dict
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from urllib3.exceptions import ReadTimeoutError

from app import logger, sentry_sdk
from app.api.instagram_proxy import get_light_posts_from_hashtag
from app.api.radarly_api import retrieve_radarly_publications
from app.dao import PostDAO, ScrapingAttemptDAO, SearchQueryLogDAO
from automated_moderation.dataset import BasePost
from selenium_driver.search_driver import SeleniumSearch
from selenium_driver.settings import DEFAULT_LOADING_TIMEOUT
from app.service.scrape_post_info import upload_post_images
from app.service.scrape_poster_info import format_poster_url
from app.models.enums import RequestResult
from app.helpers.utils import get_search_query_by_urls

post_dao = PostDAO()
scraping_attempt_dao = ScrapingAttemptDAO()
search_query_log_dao = SearchQueryLogDAO()


def get_max_results(config):
    """Return Maximum number of post urls to return"""

    return config.max_posts_to_browse


def get_all_results(
    driver: SeleniumSearch,
    search_query_by_urls: Dict[str, str],
    retry: int,
    task_log_id: int,
    search_pages_browsing_module,
    identifiers_retriever_module,
    load_more_results_module,
    max_results,
    max_posts_to_discover: int,
    action_before_search_pages_browsing_module=None,
    scrape_search_results=False,
    organisation_name=None,
    scroll_down_after_get_new_page=False,
    existing_platform_ids: set = set(),
):
    """Iterate over all the search URLs and get all the URLs available"""

    results = dict()
    total_results = 0

    l = list(search_query_by_urls.items())
    random.shuffle(l)
    search_query_by_urls = dict(l)

    for search_url, search_query in search_query_by_urls.items():
        search_query_log = search_query_log_dao.create(
            search_query=search_query, search_url=search_url, task_log_id=task_log_id
        )

        search_results = dict()
        posts_discovered = set()
        for current_attempt in range(retry):
            try:
                search_results, posts_discovered = process_search_url(
                    driver=driver,
                    search_url=search_url,
                    search_query=search_query,
                    search_pages_browsing_module=search_pages_browsing_module,
                    identifiers_retriever_module=identifiers_retriever_module,
                    load_more_results_module=load_more_results_module,
                    max_results=(max_results - len(results)),
                    action_before_search_pages_browsing_module=action_before_search_pages_browsing_module,
                    scrape_search_results=scrape_search_results,
                    organisation_name=organisation_name,
                    scroll_down_after_get_new_page=scroll_down_after_get_new_page,
                    existing_platform_ids=existing_platform_ids,
                    max_posts_to_discover=max_posts_to_discover,
                )
                results.update(search_results)
                break
            except ReadTimeoutError as e:
                logger.info(f"connection to the driver is lost {search_url} on attempt #{current_attempt}: {repr(e)}")
                with sentry_sdk.push_scope() as scope:
                    scope.set_extra("search_url", search_url)
                    scope.set_extra("search_attempt", current_attempt)
                    scope.set_extra("error_message", "ReadTimeoutError :connection to the driver is lost")
                    sentry_sdk.capture_exception(e)
                driver.reload_driver()
            except Exception as e:
                logger.info(f"Exception when scraping search url {search_url} on attempt #{current_attempt}: {repr(e)}")
                with sentry_sdk.push_scope() as scope:
                    scope.set_extra("search_url", search_url)
                    scope.set_extra("search_attempt", current_attempt)
                    scope.set_extra("error_message", "Exception when scraping search url")
                    sentry_sdk.capture_exception(e)

        if not search_results:
            logger.info("Failed to scrape search url {search_url}, max attempts exceeded")
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("search_url", search_url)
                sentry_sdk.capture_message("Failed to scrape search url max attempts exceeded")

        search_query_log_dao.end(
            search_query_log.id,
            number_of_posts_browsed=len(search_results),
            max_posts_to_browse=max_results,
            max_posts_to_discover=max_posts_to_discover,
            number_of_posts_discovered=len(posts_discovered),
        )

        if len(results) >= max_results:
            break

    logger.info(f"Results loading completed: {len(results)} results in total")

    return results, total_results


def process_search_url(
    driver: SeleniumSearch,
    search_url,
    search_query,
    search_pages_browsing_module,
    identifiers_retriever_module,
    load_more_results_module,
    max_results,
    max_posts_to_discover,
    action_before_search_pages_browsing_module=None,
    scrape_search_results=False,
    organisation_name=None,
    scroll_down_after_get_new_page=False,
    existing_platform_ids: set = set(),
):
    logger.info(f"Searching in URL {search_url}")

    search_results = dict()
    posts_discovered = set()

    scraping_attempt = driver.get(search_url, loading_delay=search_pages_browsing_module.loading_delay)

    if action_before_search_pages_browsing_module:
        driver.get_action_retriever_module_value(
            action_before_search_pages_browsing_module,
            "action_before_search_pages_browsing_module",
        )
    logger.info(f"Search page loaded for {search_url}")

    loaded_page = 1
    # For a page that is loading slowly but still keeps bringing new results it's worth to try and wait some more.
    # But if it stops making progress, we only do 2 retries and then quit.
    total_retries = 10
    sequential_retries = 2

    while True:
        if scroll_down_after_get_new_page:
            driver.scroll_down_smoothly()

        count = len(search_results)
        posts_discovered_count = len(posts_discovered)

        if scrape_search_results:
            page_results, current_posts_discovered = get_urls_from_page_with_data(
                config=search_pages_browsing_module,
                identifiers_retriever_module=identifiers_retriever_module,
                organisation_name=organisation_name,
                selenium_driver=driver,
                max_results=(max_results - len(search_results)),
                search_url=search_url,
                loaded_page=loaded_page,
                search_results=search_results,
                search_query=search_query,
                existing_platform_ids=existing_platform_ids,
            )
        else:
            page_results = driver.get_urls_from_page(
                config=identifiers_retriever_module, max_results=(max_results - len(search_results))
            )
            # FIXME: We need to implement the logic for current_posts_discovered in get_urls_from_page
            current_posts_discovered = 0

        search_results.update(page_results)
        posts_discovered.update(current_posts_discovered)

        if len(search_results) >= max_results or len(posts_discovered) >= max_posts_to_discover:
            break

        # Avoid endless looping on the same results
        if count == len(search_results) and posts_discovered_count == len(posts_discovered):
            # no progress
            if total_retries == 0 or sequential_retries == 0:
                break
            total_retries -= 1
            sequential_retries -= 1

        else:
            # we have some progress, reset the sequential_retries
            sequential_retries = 2

        if len(page_results) == 0:
            logger.info(
                f"zero results on this iteration ({len(search_results)} so far), will try again for {search_url}"
            )

            if len(search_results) == 0 and sequential_retries == 0:
                logger.info(f"probably a blank page, trying to refresh it to get results for {search_url}")
                driver.driver.refresh()

                if action_before_search_pages_browsing_module:
                    driver.get_action_retriever_module_value(
                        action_before_search_pages_browsing_module,
                        "action_before_search_pages_browsing_module",
                    )

                logger.info(f"done refreshing for {search_url}")
        else:
            logger.info(f"loading more results ({len(search_results)} so far) for {search_url}")

            driver.load_more_results(load_more_results_module, action_before_search_pages_browsing_module)
            loaded_page += 1

        if search_pages_browsing_module.loading_delay:
            time.sleep(search_pages_browsing_module.loading_delay)

    logger.info(f"Scraped {len(search_results)} results from {search_url}")

    if not search_results:
        reason = "No results found"
        logger.error(reason)
        scraping_attempt_dao.update_result(
            scraping_attempt_id=scraping_attempt.id,
            result=RequestResult.SCRAPING_FAILURE,
            error_message=reason,
        )

    return search_results, posts_discovered


def get_urls_from_page_with_data(
    selenium_driver,
    config,
    identifiers_retriever_module,
    search_results,
    search_query: str,
    organisation_name=None,
    max_results: Optional[int] = None,
    search_url: Optional[str] = None,
    loaded_page: Optional[int] = None,
    existing_platform_ids: set = set(),
) -> dict():
    """
    Config options:
        - css_selector (required): css selector to retrieve brut post identifiers
        - regex (required): regex used to filter brut content of css selector
    """

    driver = selenium_driver.driver
    listing_container_css_selector = config.listing_container_css_selector
    hover_over_listing_elements = config.hover_over_listing_elements

    listing_elements_list = driver.wait_and_find_elements(By.CSS_SELECTOR, listing_container_css_selector)
    posts_discovered = set()
    logger.info(f"Looping through {len(listing_elements_list)} listings in search page")

    listings = {}
    # FIXME StaleElementReferenceException
    # While the page is still loading in the background, elements from listing_elements_list may become stale
    # As an option, we could rerun search for listing_container_css_selector in an outer loop and repeat
    # until either the number of listings stop growing or max_results are reached.

    for listing in listing_elements_list:
        try:
            if hover_over_listing_elements:
                # Hover over listing item beofre fetching data
                try:
                    ActionChains(driver).move_to_element(listing).pause(0.01).perform()
                except Exception as e:
                    logger.info(
                        f"Exception on get_urls_from_page_with_data while hover_over_listing_elements. Exception: {repr(e)}"
                    )

            # FIXME This is a bit wierd: we're trying to narrow the search tree but it doesn't work for half of the websites and falls back to search inside "listing".
            # Since we are in the critical part of the scraping (getting the post list) it was resulting in a useless sleep of DEFAULT_REQUIRED_LOADING_TIMEOUT seconds.
            # Downgrading the timeout to DEFAULT_LOADING_TIMEOUT seconds for now.
            if identifiers_retriever_module.css_selector not in listing_container_css_selector:
                # if the listing selector is different from the identifier
                listing_item = driver.wait_and_find_elements(
                    By.CSS_SELECTOR,
                    identifiers_retriever_module.css_selector,
                    timeout=DEFAULT_LOADING_TIMEOUT,
                    root_element=listing,
                )
                if listing_item:
                    listing_item = listing_item[0]
            else:
                listing_item = listing

            post_identifier = selenium_driver.get_post_identifier(listing_item, identifiers_retriever_module)

            if post_identifier:
                posts_discovered.add(post_identifier)

            if (
                (not post_identifier)
                or (post_identifier in search_results)
                or (post_identifier in existing_platform_ids)
            ):
                logger.info(
                    f"Skipping listing: not post_identifier:{not post_identifier} - post_identifier in search_results: {post_identifier in search_results} - post_identifier in existing_platform_ids {post_identifier in existing_platform_ids}"
                )
                # valid posts discovered and skipped
                continue

            post_url = config.post_url_template.format(post_identifier)
            logger.info(f"Working with post url {post_url}")
            picture_urls = selenium_driver.get_field_retriever_module_value(
                config.pictures_retriever_module,
                "pictures_retriever_module",
                listing,
            )
            listing_data = {
                "organisation_names": [organisation_name] if organisation_name else [],
                "id": post_identifier,
                "scraping_time": datetime.today().strftime("%Y-%m-%d-%H:%M:%S"),
                "url": post_url,
                "archive_link": None,
                "description": None,
                "posting_time": None,
                "location": selenium_driver.get_field_retriever_module_value(
                    config.location_retriever_module, "location_retriever_module", listing
                ),
                "ships_from": None,
                "ships_to": None,
                "title": selenium_driver.get_field_retriever_module_value(
                    config.title_retriever_module, "title_retriever_module", listing
                ),
                "price": selenium_driver.get_field_retriever_module_value(
                    config.price_retriever_module, "price_retriever_module", listing
                ),
                "vendor": selenium_driver.get_field_retriever_module_value(
                    config.vendor_retriever_module, "vendor_retriever_module", listing
                ),
                "poster_link": selenium_driver.get_field_retriever_module_value(
                    config.poster_link_retriever_module,
                    "poster_link_retriever_module",
                    listing,
                ),
                "pictures": upload_post_images(picture_urls, selenium_driver) if picture_urls else [],
                "videos": selenium_driver.get_field_retriever_module_value(
                    config.videos_retriever_module, "videos_retriever_module", listing
                ),
                "item_sold": selenium_driver.get_field_retriever_module_value(
                    config.item_sold_retriever_module, "item_sold_retriever_module", listing
                ),
                "search_url": search_url,
                "loaded_page": loaded_page,
                "index_on_page": len(listings) + 1,
                "tags": [f"search_query:{search_query}"],
            }
            logger.info(f"Scraped Data : {listing_data}")
            if post_identifier not in listings:
                listings[post_identifier] = listing_data

            if max_results and len(listings) >= max_results:
                break
        except Exception as e:
            logger.info("Exception on get_urls_from_page_with_data")
            logger.info(str(e))
            continue

    logger.info(f"Returning : {len(listings)} listings")
    return listings, posts_discovered


def search_keywords_with_selenium(
    domain_name,
    task_log_id: int,
    config,
    keywords=None,
    max_results=None,
    scrape_search_results=False,
    organisation_name=None,
    search_urls=None,
    existing_platform_ids: set = set(),
    max_posts_to_discover=None,
):
    logger.info(f"Launching Selenium driver for domain {domain_name, config}")

    driver = SeleniumSearch(domain_name=domain_name, config=config)
    search_config = config.search_pages_browsing_module

    if search_urls is None:
        search_query_by_urls = get_search_query_by_urls(config=search_config, queries=keywords)
    else:
        search_query_by_urls = {search_url: search_url for search_url in search_urls}

    logger.info(f"Searching with search URLs: {search_urls}")

    if not max_results:
        max_results = get_max_results(config=search_config)

    results, total_results = get_all_results(
        driver,
        search_query_by_urls,
        retry=6 if config.proxies else 3,
        search_pages_browsing_module=search_config,
        identifiers_retriever_module=search_config.post_identifiers_retriever_module,
        load_more_results_module=search_config.load_more_results_module,
        task_log_id=task_log_id,
        max_results=max_results,
        action_before_search_pages_browsing_module=search_config.action_before_search_pages_browsing_module,
        scrape_search_results=scrape_search_results,
        organisation_name=organisation_name,
        scroll_down_after_get_new_page=search_config.scroll_down_after_get_new_page,
        existing_platform_ids=existing_platform_ids,
        max_posts_to_discover=max_posts_to_discover,
    )

    driver.kill_driver()

    return results, total_results


def search_posters_with_selenium(
    domain_name,
    poster_urls,
    config,
    task_log_id,
    organisation_name=None,
    max_results=None,
    scrape_search_results=False,
    max_posts_to_discover=None,
):
    logger.info(f"Launching Selenium Driver for Domain {domain_name}")

    driver = SeleniumSearch(domain_name=domain_name, config=config)

    logger.info(f"Searching posters from poster URLs: {poster_urls}")

    # format urls
    formated_poster_urls = {}
    for poster_url in poster_urls:
        formated_poster_url = format_poster_url(config, poster_url)
        formated_poster_urls[formated_poster_url] = formated_poster_url

    logger.info(f"Formated poster URLs: {poster_urls}")

    search_config = config.search_pages_browsing_module
    # Cater for cases with no poster_post_identifiers_retriever_module
    if search_config.poster_post_identifiers_retriever_module is None:
        return [], 0

    # Use action before within poster_post_identifier_retriever_module if present
    search_config.action_before_search_pages_browsing_module = (
        search_config.poster_post_identifiers_retriever_module.action_before_poster_post_identifiers_module
        if search_config.poster_post_identifiers_retriever_module.action_before_poster_post_identifiers_module
        else search_config.action_before_search_pages_browsing_module
    )

    #  load poster search related search_config , otherwise fallback to default - this caters for search/poster page that use different selectors
    load_more_results_module = (
        search_config.poster_post_identifiers_retriever_module.load_more_results_module
        if search_config.poster_post_identifiers_retriever_module.load_more_results_module
        else search_config.load_more_results_module
    )
    search_config.listing_container_css_selector = (
        search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.listing_container_css_selector
    )
    search_config.pictures_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.pictures_retriever_module
        # To make sure the scraper doesn't fall back to main listing selectors if any field is NA
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.pictures_retriever_module
    )
    search_config.videos_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.videos_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.videos_retriever_module
    )
    search_config.title_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.title_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.title_retriever_module
    )
    search_config.description_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.description_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.description_retriever_module
    )
    search_config.price_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.price_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.price_retriever_module
    )
    search_config.vendor_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.vendor_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.vendor_retriever_module
    )
    search_config.poster_link_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.poster_link_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.poster_link_retriever_module
    )
    search_config.location_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.location_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.location_retriever_module
    )
    search_config.item_sold_retriever_module = (
        search_config.poster_post_identifiers_retriever_module.item_sold_retriever_module
        if search_config.poster_post_identifiers_retriever_module.listing_container_css_selector
        else search_config.item_sold_retriever_module
    )

    if not max_results:
        max_results = get_max_results(config=search_config)

    results, total_results = get_all_results(
        driver,
        formated_poster_urls,
        retry=6 if config.proxies else 3,
        task_log_id=task_log_id,
        organisation_name=organisation_name,
        search_pages_browsing_module=search_config,
        identifiers_retriever_module=search_config.poster_post_identifiers_retriever_module,
        load_more_results_module=load_more_results_module,
        max_results=max_results,
        action_before_search_pages_browsing_module=search_config.action_before_search_pages_browsing_module,
        scrape_search_results=scrape_search_results,
        scroll_down_after_get_new_page=search_config.scroll_down_after_get_new_page,
        max_posts_to_discover=max_posts_to_discover,
    )

    driver.kill_driver()

    return results, total_results


def instagram_hashtags_posts_search(
    hashtags, max_posts_to_browse: int, max_attempts: Optional[int] = 3
) -> List[BasePost]:
    """Retrieve the posts published on Instagram corresponding to a list of hashtags using hashtag search

    Parameters:
    ===========
    hashtags: str[]
    concurrency: int
    rescrape: bool
        whether or not to rescrape posts which are already stored in database

    Returns:
    ========
    posts: dict
        {shortcode: post_content}
    """

    # Make sure that the hashtags used as arguments are unique, lowercase, stripped and sorted
    hashtags = sorted(list(set([h.lower().strip() for h in hashtags])))

    post_hashtags_mapping = dict()

    # Get the resulting shortcodes
    all_light_posts = []

    logger.info(f"Scraping {len(hashtags)} hashtags...")

    random.shuffle(hashtags)

    for cnt, hashtag in enumerate(hashtags):
        new_light_posts = get_light_posts_from_hashtag(
            hashtag,
            max_posts_to_browse=(max_posts_to_browse - len(all_light_posts)),
            max_attempts=max_attempts,
        )
        logger.info(f"({cnt + 1}/{len(hashtags)}) The hashtag {hashtag} retrieves {len(new_light_posts)} posts")

        for post in new_light_posts:
            if post.id not in post_hashtags_mapping:
                all_light_posts.append(post)

        # Update the post -> hashtags mapping
        for post in new_light_posts:
            post_hashtags_mapping.setdefault(post.id, []).append(hashtag)

        if len(all_light_posts) >= max_posts_to_browse:
            break

    return all_light_posts


def radarly_search(
    organisation_name: str,
    domain_name: str,
    search_queries: list,
    post_id_regex: str,
    previous_run_time: datetime,
) -> List[BasePost]:
    if previous_run_time:
        start_date = previous_run_time
    else:
        # Use the crawling date of the last post added to determine the range to filter by
        start_date = post_dao.get_date_of_last_post_crawled(organisation_name, domain_name)

    # Substract 3 days to the date of the previous run time or crawling to be sure to catch all of Radarly's results
    start_date -= timedelta(days=3)

    posts = []
    for query_label in search_queries:
        posts.extend(
            retrieve_radarly_publications(
                query_label,
                start_date,
                domain_name=domain_name,
                post_identifier_regex=post_id_regex,
            )
        )

    # Remove the duplicates and the posts already scraped
    new_posts = post_dao.select_not_scraped_and_unique_posts(posts, organisation_name, domain_name)

    return new_posts
