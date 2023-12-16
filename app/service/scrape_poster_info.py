from datetime import datetime
from multiprocessing.pool import ThreadPool
import re
from tqdm import tqdm

from app import logger
from app.api.instagram_proxy import get_profile_multithreading
from app.dao import PosterDAO, RedisDAO
from app.helpers.utils import clean_url
from app.service.login import login
from selenium_driver.main_driver import Selenium

redis_DAO = RedisDAO()
poster_DAO = PosterDAO()


def format_poster_url(config, poster_identifier):
    "Format Poster URL"
    if (
        not config.poster_information_retriever_module
        and not config.poster_information_retriever_module.poster_url_template
    ):
        return poster_identifier

    poster_url = config.poster_information_retriever_module.poster_url_template.format(poster_identifier)

    # this caters for cases such as yupoo where we need to append a new value to the url if it doesnt exist
    # Example yupoo should have /categories/ in the url otherwise leave with a trailing /categories for default list
    if (
        config.poster_information_retriever_module.poster_url_replace_old_regex is not None
        and config.poster_information_retriever_module.poster_url_replace_new is not None
    ):
        poster_url = re.sub(
            config.poster_information_retriever_module.poster_url_replace_old_regex,
            f"{poster_url.rstrip('/')}{config.poster_information_retriever_module.poster_url_replace_new}",
            poster_url,
        )
    return poster_url


def scrape_poster_with_selenium(
    domain_name: str,
    config,
    poster_urls,
    upload_request_id=None,
    upload_account_identifier_url_mapping=None,
):
    if upload_account_identifier_url_mapping is None:
        upload_account_identifier_url_mapping = dict()
    scraped_data = []
    record_redirection_url = config.poster_information_retriever_module.record_redirection_url

    # When using api_selenium_framework, search driver is different(requests) from poster retrieval driver(selenium).
    # So we need to pass Selenium driver config when scraping poster information
    if config.post_information_retriever_module.driver_initialization_module:
        config.driver_initialization_module = config.post_information_retriever_module.driver_initialization_module

    selenium_driver = Selenium(domain_name=domain_name, config=config)

    if config.login_module:
        login(selenium_driver=selenium_driver, config=config.login_module)

    for poster_identifier in tqdm(poster_urls):
        upload_id = upload_account_identifier_url_mapping.get(poster_identifier)
        try:
            poster_url = format_poster_url(config, poster_identifier)

            logger.info(f"Scraping {poster_url}")
            selenium_driver.get(
                poster_url,
                loading_delay=config.poster_information_retriever_module.loading_delay,
            )

            if config.poster_information_retriever_module.action_before_retrieving_post_information_module:
                selenium_driver.get_action_retriever_module_value(
                    config.poster_information_retriever_module.action_before_retrieving_post_information_module,
                    "action_before_retrieving_post_information_module",
                )

            if selenium_driver.driver.current_url != poster_url and record_redirection_url:
                logger.info(f"Redirection url {poster_url} to {selenium_driver.driver.current_url}")

                try:
                    poster_url = clean_url(selenium_driver.driver.current_url, config.poster_url_cleaning_module)
                except Exception as ex:
                    logger.warn(f"Exception on {poster_url} redirect {str(ex)}")

            poster_information = _get_poster_information(
                poster_identifier=poster_identifier,
                selenium_driver=selenium_driver,
                poster_url=poster_url,
                config=config,
            )

            logger.info(f"Scraping Poster information completed {poster_url}: {poster_information}")

            if poster_information:
                status = "ended"
                scraped_data.append(poster_information)
            else:
                status = "failed"
            if upload_request_id:
                logger.info(f"Upload status for {poster_identifier} is '{status}'")
                redis_DAO.set_url_upload_status(upload_request_id, upload_id, status)

        except Exception as ex:
            logger.warn(f"Error scraping {poster_identifier} , {str(ex)}")

            if upload_request_id:
                logger.info(f"Upload status for {poster_identifier} is 'failed'")
                redis_DAO.set_url_upload_status(upload_request_id, upload_id, "failed")
            continue

    selenium_driver.kill_driver()
    return scraped_data


def _get_poster_information(poster_identifier, selenium_driver, poster_url, config):
    """Get Post Information from loaded post url"""
    take_screenshot = config.poster_information_retriever_module.take_screenshot

    return {
        "id": poster_identifier,
        "url": poster_url,
        "scraping_time": datetime.today(),
        "archive_link": selenium_driver.take_webshot() if take_screenshot else None,
        "name": selenium_driver.get_field_retriever_module_value(
            config.poster_information_retriever_module.poster_name_retriever_module,
            "poster_name_retriever_module",
        ),
        "followers_count": selenium_driver.get_field_retriever_module_value(
            config.poster_information_retriever_module.followers_count_retriever_module,
            "followers_count_retriever_module",
        ),
        "description": selenium_driver.get_field_retriever_module_value(
            config.poster_information_retriever_module.description_retriever_module,
            "description_retriever_module",
        ),
        "profile_pic_url": (lambda x: x[0] if x != [] and type(x) == list else "")(
            selenium_driver.get_field_retriever_module_value(
                config.poster_information_retriever_module.picture_retriever_module,
                "picture_retriever_module",
            )
        ),
        "payload": selenium_driver.get_field_retriever_module_value(
            config.poster_information_retriever_module.payload_retriever_module,
            "payload_retriever_module",
        ),
    }


def scrape_instagram_profiles(
    usernames,
    user_id_by_username=dict(),
    concurrency=8,
    rescrape=True,
    upload_request_id=None,
    upload_accounts_batch=[],
    upload_account_identifier_url_mapping=dict(),
):
    """Retrieve the profiles of Instagram usernames

    Parameters:
    ===========
    usernames: str[]
    username_user_id_mapping: dict
        {"username": "user_id"}
        useful to scrape profiles using their user ID instead of username
    concurrency: int
    rescrape: bool
        whether or not to rescrape posts which are already stored in database
    upload_request_id: int or None
        useful to set the URL upload status if the scraping of an account fails
    upload_accounts_batch: dict[]
        useful to get the upload_id to set the status in Redis in case of failure
    upload_account_identifier_url_mapping: dict
        useful to get the original URL submitted for upload

    Returns:
    ========
    profiles: dict
        {username: profile_content}
    """

    # Build a dictionary account URL: account upload request object
    username_upload_id_map = {
        account_request.get("username"): account_request.get("upload_id") for account_request in upload_accounts_batch
    }

    if rescrape:
        usernames_to_scrape = usernames
    else:
        usernames_to_scrape = poster_DAO.get_unscraped_instagram_usernames(usernames)
        logger.info(
            f"Not rescraping already scraped profiles - {len(usernames) - len(usernames_to_scrape)}/{len(usernames)} profiles were already known to the database"
        )

    logger.info(f"Scraping information for {len(usernames_to_scrape)} usernames ({concurrency} by {concurrency})...")

    args = [(username, user_id_by_username.get(username)) for username in usernames_to_scrape]
    with ThreadPool(concurrency) as p:
        posters = tqdm(p.imap(get_profile_multithreading, args, chunksize=8), total=len(args))
        posters = {username: profile_details for batch in posters for username, profile_details in batch.items()}

    if upload_request_id:
        for username in usernames_to_scrape:
            upload_id = username_upload_id_map.get(username)
            if upload_id is None:
                logger.info(f"username without upload_id {username}")
                continue
            status = "ended" if username in posters else "failed"
            redis_DAO.set_url_upload_status(upload_request_id, upload_id, status)
            logger.info(f"{username} status is '{status}'")

    return posters
