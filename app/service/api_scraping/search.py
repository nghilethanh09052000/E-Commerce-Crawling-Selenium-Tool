from datetime import datetime
from typing import Optional, Dict, List
from app import logger

from app.service.api_scraping.api_driver import ApiDriver
from app.service.search import get_max_results
from app.helpers.utils import get_search_query_by_urls
from app.dao import SearchQueryLogDAO

search_query_log_dao = SearchQueryLogDAO()


def get_listing_data_from_result(
    response,
    api_driver: ApiDriver,
    config,
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

    tags = [f"search_query:{search_query}"] if search_query else []

    listing_elements_list = api_driver.get_field_retriever_module_value(
        module_config=config.listing_retriever_module,
        module_name="listing_retriever_module",
        response=response,
    )

    logger.info(f"Looping through {len(listing_elements_list)} listings in search page")
    listings = {}
    posts_discovered = set()
    for listing in listing_elements_list:
        try:
            post_identifier = api_driver.get_field_retriever_module_value(
                module_config=config.post_identifiers_retriever_module,
                module_name="post_identifiers_retriever_module",
                response=listing,
            )

            if post_identifier:
                posts_discovered.add(post_identifier)

            if post_identifier in existing_platform_ids:
                logger.info(
                    f"Skipping listing: post_identifier in existing_platform_ids {post_identifier in existing_platform_ids}"
                )
                continue

            if not config.post_url_template:
                post_url = post_identifier
            else:
                post_url = config.post_url_template.format(post_identifier)

            logger.info(f"Working with post url {post_url}")

            listing_data = {
                "organisation_names": [organisation_name] if organisation_name else [],
                "id": post_identifier,
                "scraping_time": datetime.today().strftime("%Y-%m-%d-%H:%M:%S"),
                "url": post_url,
                "archive_link": None,
                "description": None,
                "posting_time": None,
                "location": api_driver.get_field_retriever_module_value(
                    module_config=config.location_retriever_module,
                    module_name="location_retriever_module",
                    response=listing,
                ),
                "ships_from": None,
                "ships_to": None,
                "title": api_driver.get_field_retriever_module_value(
                    module_config=config.title_retriever_module, module_name="title_retriever_module", response=listing
                ),
                "price": api_driver.get_field_retriever_module_value(
                    module_config=config.price_retriever_module, module_name="price_retriever_module", response=listing
                ),
                "vendor": api_driver.get_field_retriever_module_value(
                    module_config=config.vendor_retriever_module,
                    module_name="vendor_retriever_module",
                    response=listing,
                ),
                "poster_link": api_driver.get_field_retriever_module_value(
                    module_config=config.poster_link_retriever_module,
                    module_name="poster_link_retriever_module",
                    response=listing,
                ),
                "pictures": api_driver.get_field_retriever_module_value(
                    module_config=config.pictures_retriever_module,
                    module_name="pictures_retriever_module",
                    response=listing,
                ),
                "videos": api_driver.get_field_retriever_module_value(
                    module_config=config.videos_retriever_module,
                    module_name="videos_retriever_module",
                    response=listing,
                ),
                "item_sold": api_driver.get_field_retriever_module_value(
                    module_config=config.item_sold_retriever_module,
                    module_name="item_sold_retriever_module",
                    response=listing,
                ),
                "search_url": search_url,
                "loaded_page": loaded_page,
                "index_on_page": len(listings) + 1,
                "tags": tags,
            }

            logger.info(f"Scraped Data : {listing_data}")
            if post_identifier not in listings:
                listings[post_identifier] = listing_data
            if max_results and len(listings) >= max_results:
                break
        except Exception as e:
            logger.info("Exception on get_listing_data_from_result")
            logger.info(str(e))
            continue

    logger.info(f"Returning : {len(listings)} listings")
    return listings, posts_discovered


def search_keywords_with_api(
    domain_name,
    config,
    max_posts_to_discover: int,
    task_log_id: int,
    keywords=None,
    max_results=None,
    organisation_name=None,
    search_urls: List[str] = None,
    existing_platform_ids: set = set(),
):
    logger.info(f"API Scraping for domain {domain_name}")

    if not max_results:
        max_results = get_max_results(config=config.search_pages_browsing_module)

    if search_urls is None:
        search_query_by_urls = get_search_query_by_urls(
            config=config.search_pages_browsing_module, queries=keywords, max_posts_to_discover=max_results
        )
    else:
        search_query_by_urls = {search_url: search_url for search_url in search_urls}

    logger.info(f"Searching with search URLs: {search_urls}")

    results, total_results = get_all_results(
        search_query_by_urls=search_query_by_urls,
        domain_name=domain_name,
        config=config,
        search_pages_browsing_module=config.search_pages_browsing_module,
        max_results=max_results,
        organisation_name=organisation_name,
        existing_platform_ids=existing_platform_ids,
        max_posts_to_discover=max_posts_to_discover,
        task_log_id=task_log_id,
    )

    return results, total_results


def search_images_with_api(
    domain_name,
    config,
    max_posts_to_discover: int,
    task_log_id: int,
    search_image_urls: List[str],
    max_results=None,
    organisation_name=None,
    search_urls: List[str] = None,
    existing_platform_ids: set = set(),
):
    logger.info(f"API Scraping for domain {domain_name}")

    if not max_results:
        max_results = get_max_results(config=config.search_pages_browsing_module)

    if search_urls is None:
        search_query_by_urls = get_search_query_by_urls(
            config=config.search_pages_browsing_module,
            queries=search_image_urls,
            max_posts_to_discover=max_results,
            template_name="image_search_page_url_templates",
        )
    else:
        search_query_by_urls = {search_url: search_url for search_url in search_urls}

    logger.info(f"Searching with search URLs: {search_urls}")

    results, total_results = get_all_results(
        search_query_by_urls=search_query_by_urls,
        domain_name=domain_name,
        config=config,
        search_pages_browsing_module=config.search_pages_browsing_module,
        max_results=max_results,
        organisation_name=organisation_name,
        existing_platform_ids=existing_platform_ids,
        max_posts_to_discover=max_posts_to_discover,
        task_log_id=task_log_id,
    )

    return results, total_results


def get_all_results(
    search_query_by_urls: Dict[str, str],
    domain_name,
    config,
    search_pages_browsing_module,
    max_results,
    max_posts_to_discover,
    task_log_id: int,
    organisation_name=None,
    existing_platform_ids: set = set(),
):
    """Iterate over all the search URLs and get all the URLs available"""

    results = dict()
    total_results = 0
    # call api driver that handles api requests
    api_driver = ApiDriver(domain_name=domain_name, config=config)

    for main_search_url, search_query in search_query_by_urls.items():
        logger.info(f"Searching in URL {main_search_url}")

        search_results = dict()
        posts_discovered = set()

        page_number = 1

        if search_pages_browsing_module.load_more_results_module:
            if search_pages_browsing_module.load_more_results_module.name == "load_more_by_adding_page":
                page_multiplier = search_pages_browsing_module.load_more_results_module.page_multiplier
                page_number = 0 if page_multiplier != 1 else 1
                page = search_pages_browsing_module.load_more_results_module.value.format(
                    PAGE_NUMBER=page_number * page_multiplier
                )
                search_url = main_search_url + page
            else:
                search_url = main_search_url
        else:
            search_url = main_search_url

        # Create search log
        search_query_log = search_query_log_dao.create(
            search_query=search_query, search_url=search_url, task_log_id=task_log_id
        )

        response = api_driver.search(search_url, search_query, max_results)

        logger.info(f"Search page loaded for {search_url}")

        loaded_page = 1
        retry_trials = 1
        while True:
            count = len(search_results)
            posts_discovered_count = len(posts_discovered)

            page_results, current_posts_discovered = get_listing_data_from_result(
                config=search_pages_browsing_module,
                organisation_name=organisation_name,
                response=response,
                max_results=(max_results - len(search_results)),
                search_url=search_url,
                loaded_page=loaded_page,
                api_driver=api_driver,
                search_query=search_query,
                existing_platform_ids=existing_platform_ids,
            )

            search_results.update(page_results)
            posts_discovered.update(current_posts_discovered)

            if len(search_results) >= max_results or len(posts_discovered) >= max_posts_to_discover:
                break

            # Avoid endless looping on the same results
            if count == len(search_results) and posts_discovered_count == len(posts_discovered):
                if retry_trials == 0:
                    # No more results
                    break

                retry_trials = retry_trials - 1

            logger.info(f"loading more results ({len(search_results)} so far)")

            page_number += 1
            loaded_page += 1

            if search_pages_browsing_module.load_more_results_module:
                if search_pages_browsing_module.load_more_results_module.name == "load_more_by_adding_page":
                    page = search_pages_browsing_module.load_more_results_module.value.format(
                        PAGE_NUMBER=page_number * page_multiplier
                    )
                    search_url = main_search_url + page
                elif search_pages_browsing_module.load_more_results_module.name == "load_more_by_field_url":
                    search_url = response.get(search_pages_browsing_module.load_more_results_module.value)
                    # if no more url , no more results
                    if search_url is None:
                        break

            logger.info(f"Searching page  for {search_url}")
            response = api_driver.search(search_url, search_query, max_results)

        logger.info(f"Scraped {len(search_results)} results from {search_url}")
        results.update(search_results)

        search_query_log_dao.end(
            search_query_log.id,
            number_of_posts_browsed=len(search_results),
            max_posts_to_browse=max_results,
            max_posts_to_discover=max_posts_to_discover,
            number_of_posts_discovered=len(posts_discovered),
        )

    logger.info(f"Results loading completed: {len(results)} results in total")

    return results, total_results
