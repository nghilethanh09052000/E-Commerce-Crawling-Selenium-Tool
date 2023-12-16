from tqdm import tqdm
from datetime import datetime
from app import logger
from app.models import Website
from app.service.scrape_post_info import save_post
from app.settings import sentry_sdk
from app.service.api_scraping.api_driver import ApiDriver
from app.helpers.utils import clean_url
from app.dao import RedisDAO, WebsiteDAO
from app.models.marshmallow.config import ScrapeSchema

website_DAO = WebsiteDAO()
redis_DAO = RedisDAO()


def scrape_post_with_api(
    website: Website,
    task_id: int,
    config,
    light_posts_to_scrape,
    upload_request_id=None,
    post_identifier_upload_id_mapping=None,
    organisation_name=None,
):
    """Scrape posts using different api providers"""
    scraped_data = []

    for post_identifier in tqdm(light_posts_to_scrape):
        try:
            post_url = config.post_information_retriever_module.post_url_template.format(post_identifier)
            endpoint_post_url = config.post_information_retriever_module.endpoint_post_url_template.format(
                post_identifier
            )

            logger.info(f"Scraping {post_url}")
            # call api driver that handles api requests
            api_driver = ApiDriver(domain_name=website.domain_name, config=config)
            response = api_driver.scrape_post(endpoint_post_url)

            logger.info(f" API Response {str(response)}")

            post_url = clean_url(
                post_url, config.search_pages_browsing_module.post_identifiers_retriever_module.post_url_cleaning_module
            )

            post_information = _get_post_information(
                post_identifier=post_identifier,
                response=response,
                post_url=post_url,
                config=config,
                organisation_name=organisation_name,
                api_driver=api_driver,
            )

            post_information["light_post_payload"] = light_posts_to_scrape[post_identifier] or {}
            post_information["risk_score"] = (
                light_posts_to_scrape[post_identifier].get("risk_score", 0)
                if light_posts_to_scrape[post_identifier]
                else None
            )
            post_information["tags"] = (
                light_posts_to_scrape[post_identifier].get("tags", []) if light_posts_to_scrape[post_identifier] else []
            )
            post_information["skip_filter_scraped_results"] = (
                light_posts_to_scrape[post_identifier].get("skip_filter_scraped_results", False)
                if light_posts_to_scrape[post_identifier]
                else False
            )

            logger.info(f"Scraping Post information completed {post_url}: {post_information}")

            if post_information:
                scraped_data.append(post_information)
                save_post(post=post_information, website=website, task_id=task_id)

        except Exception as ex:
            logger.warn(f"Error scraping {post_identifier} , {str(ex)}")

            if upload_request_id:
                redis_DAO.set_url_upload_status(
                    upload_request_id,
                    post_identifier_upload_id_mapping[post_identifier],
                    "failed",
                )
            sentry_sdk.capture_exception(ex)
            continue

    return scraped_data


def _get_post_information(
    post_identifier, response, post_url, config: ScrapeSchema, api_driver: ApiDriver, organisation_name=None
):
    """Get Post Information from loaded post url"""

    return {
        "organisation_names": [organisation_name] if organisation_name else [],
        "id": post_identifier,
        "scraping_time": datetime.today().strftime("%Y-%m-%d-%H:%M:%S"),
        "url": post_url,
        "title": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.title_retriever_module,
            module_name="title_retriever_module",
            response=response,
        ),
        "description": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.description_retriever_module,
            module_name="description_retriever_module",
            response=response,
        ),
        "price": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.price_retriever_module,
            module_name="price_retriever_module",
            response=response,
        ),
        "stock_count": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.stock_retriever_module,
            module_name="stock_retriever_module",
            response=response,
        ),
        "vendor": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.vendor_retriever_module,
            module_name="vendor_retriever_module",
            response=response,
        ),
        "poster_link": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.poster_link_retriever_module,
            module_name="poster_link_retriever_module",
            response=response,
        ),
        "posting_time": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.date_retriever_module,
            module_name="date_retriever_module",
            response=response,
        ),
        "location": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.location_retriever_module,
            module_name="location_retriever_module",
            response=response,
        ),
        "ships_from": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.ships_from_retriever_module,
            module_name="ships_from_retriever_module",
            response=response,
        ),
        "ships_to": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.ships_to_retriever_module,
            module_name="ships_to_retriever_module",
            response=response,
        ),
        "pictures": api_driver.get_field_retriever_module_value(
            module_config=config.post_information_retriever_module.pictures_retriever_module,
            module_name="pictures_retriever_module",
            response=response,
        ),
        # "videos": api_driver.get_field_retriever_module_value(
        #     module_config=config.post_information_retriever_module.videos_retriever_module,
        #     module_name="videos_retriever_module",
        #     response=response,
        # ),
        # "archive_link": selenium_driver.take_webshot() if take_screenshot else None,
    }
