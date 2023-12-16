from datetime import datetime, timezone
from typing import List, Dict
from multiprocessing.pool import ThreadPool
import time

from tqdm import tqdm

from app import logger
from app.api.instagram_proxy import get_post_multithreading, get_profile_posts
from app.dao import PostDAO, RedisDAO, ScrapingAttemptDAO, OrganisationDAO
from app.helpers.utils import clean_url
from app.models import Website
from app.models.enums import RequestResult
from app.service.login import login
from app.settings import sentry_sdk
from selenium_driver.main_driver import Selenium
from selenium_driver.helpers.s3 import upload_image_from_bytes, upload_image_from_url
from automated_moderation.dataset import BasePost
from app.models.marshmallow.config import ScrapeSchema

redis_DAO = RedisDAO()
post_DAO = PostDAO()
scraping_attempt_DAO = ScrapingAttemptDAO()
organisation_DAO = OrganisationDAO()


class SlowFailException(Exception):
    pass


class FastFailException(Exception):
    pass


def scrape_posts_with_selenium(
    website: Website,
    config,
    light_posts_to_scrape,
    task_id: int,
    upload_request_id=None,
    organisation_name=None,
):
    scraped_data = []

    # When using api_selenium_framework, search driver is different(requests) from post retrieval driver(selenium).
    # So we need to pass Selenium driver config when scraping posts
    if config.post_information_retriever_module.driver_initialization_module:
        config.driver_initialization_module = config.post_information_retriever_module.driver_initialization_module

    selenium_driver = Selenium(domain_name=website.domain_name, config=config)

    """
    About retries:
      * FAST retry = refreshing the page + retrying _get_post_information
      * SLOW retry = killing the driver + re-selecting the proxy + scraping from scratch

    Fast retries preserve the browser cache so it should be the best strategy on slow connections.
    Slow retries are needed e.g. to change IP when detected or fix some grave issue with the driver.

    Total attempts are (max_slow_retries+1) x (max_fast_retries+1)
    """

    max_slow_retries = 1
    max_fast_retries = 1

    for post_identifier in tqdm(light_posts_to_scrape):
        post_information = None
        for current_slow_attempt in range(max_slow_retries + 1):
            try:
                post_information = scrape_one_post_with_selenium(
                    config=config,
                    selenium_driver=selenium_driver,
                    post_identifier=post_identifier,
                    light_post=light_posts_to_scrape.get(post_identifier, {}),
                    max_fast_retries=max_fast_retries,
                    organisation_name=organisation_name,
                )
                break

            except Exception as ex:
                logger.warn(f"ERROR scraping {post_identifier} on SLOW attempt #{current_slow_attempt}: {str(ex)}")

        if post_information:
            scraped_data.append(post_information)
            logger.info(
                f"SUCCESS scraping {post_identifier} on SLOW attempt #{current_slow_attempt}"
                + (", SLOW retry helped!" if current_slow_attempt > 0 else "")
            )

            save_post(post=post_information, website=website, task_id=task_id)
        else:
            logger.info(f"FAIL scraping {post_identifier}, SLOW retry count {max_slow_retries} exceeded")

    selenium_driver.kill_driver()
    return scraped_data


def save_post(post: Dict, website: Website, task_id: int):
    for organisation_name in post.get("organisation_names", [None]):
        organisation = organisation_DAO.get(organisation_name=organisation_name) if organisation_name else None

        post_DAO.save_scraped_post(
            post_data=post,
            organisation_id=organisation and organisation.id,
            website_id=website.id,
            task_id=task_id,
        )

        post_DAO.update_post(
            post_data=post,
            organisation_id=organisation and organisation.id,
            website_id=website.id,
            task_id=task_id,
        )


def scrape_one_post_with_selenium(
    config,
    selenium_driver: Selenium,
    post_identifier,
    light_post,
    max_fast_retries,
    organisation_name,
):
    post_url = config.post_information_retriever_module.post_url_template.format(post_identifier)
    record_redirection_url = config.post_information_retriever_module.record_redirection_url
    auto_kill_driver = (
        True
        if config.post_information_retriever_module.name
        == "post_information_retriever_with_creation_of_a_new_driver_for_each_post_module"
        else False
    )

    # FIXME This doesn't look right because we can kill the driver inside get
    # Didn't touch it during the refactoring, but it needs to be fixed.
    if config.login_module:
        login(selenium_driver=selenium_driver, config=config.login_module)

    logger.info(f"Scraping {post_url}")
    scraping_attempt = selenium_driver.get(
        post_url,
        loading_delay=config.post_information_retriever_module.loading_delay,
        auto_kill_driver=auto_kill_driver,
    )

    if config.post_information_retriever_module.action_before_retrieving_post_information_module:
        selenium_driver.get_action_retriever_module_value(
            config.post_information_retriever_module.action_before_retrieving_post_information_module,
            "action_before_retrieving_post_information_module",
        )

    if selenium_driver.driver.current_url != post_url and record_redirection_url:
        logger.info(f"Redirection url {post_url} to {selenium_driver.driver.current_url}")

        try:
            post_url = clean_url(selenium_driver.driver.current_url, config.post_url_cleaning_module)
        except Exception as ex:
            scraping_attempt_DAO.update_result(
                scraping_attempt_id=scraping_attempt.id,
                result=RequestResult.SCRAPING_FAILURE,
                error_message=f"failed to clean_url: {repr(ex)}",
            )
            raise SlowFailException(f"SLOW FAIL on {post_url} redirect: {repr(ex)}")

    post_information = None
    reason = ""
    for current_fast_attempt in range(max_fast_retries + 1):
        try:
            if current_fast_attempt:
                logger.info(f"Refreshing the page for {post_url}")
                selenium_driver.driver.refresh()

            post_information = _get_post_information(
                post_identifier=post_identifier,
                selenium_driver=selenium_driver,
                post_url=post_url,
                config=config,
                organisation_name=organisation_name,
            )
            logger.info(
                f"Success on {post_url} _get_post_information FAST attempt #{current_fast_attempt}"
                + (", FAST retry helped!" if current_fast_attempt > 0 else "")
            )
            break
        except Exception as ex:
            reason = repr(ex)
            logger.warn(f"Exception on {post_url} _get_post_information FAST attempt #{current_fast_attempt}: {reason}")

    if not post_information:
        scraping_attempt_DAO.update_result(
            scraping_attempt_id=scraping_attempt.id,
            result=RequestResult.SCRAPING_FAILURE,
            error_message=reason or "_get_post_information returned nothing",
        )
        raise SlowFailException(
            f"SLOW FAIL on {post_url} _get_post_information, exceeded FAST retry count {max_fast_retries}"
        )

    post_information["light_post_payload"] = light_post
    post_information["risk_score"] = light_post.get("risk_score")
    post_information["tags"] = light_post.get("tags", [])
    post_information["skip_filter_scraped_results"] = light_post.get("skip_filter_scraped_results", False)

    logger.info(f"Scraping Post information completed {post_url}: {post_information}")

    return post_information


def _get_post_information(
    post_identifier, selenium_driver: Selenium, post_url, config: ScrapeSchema, organisation_name=None
):
    """Get Post Information from loaded post url"""
    take_screenshot = config.post_information_retriever_module.take_screenshot

    title = selenium_driver.get_field_retriever_module_value(
        config.post_information_retriever_module.title_retriever_module,
        "title_retriever_module",
    )

    description = selenium_driver.get_field_retriever_module_value(
        config.post_information_retriever_module.description_retriever_module,
        "description_retriever_module",
    )

    # TODO: FastFail should be bound to the same list of fields as in post_should_be_saved
    if not title and not description:
        raise FastFailException(f"FastFail for post {post_url}: neither title nor description scraped")

    picture_urls = selenium_driver.get_field_retriever_module_value(
        config.post_information_retriever_module.pictures_retriever_module,
        "pictures_retriever_module",
    )

    if not picture_urls:
        raise FastFailException(f"FastFail for post {post_url}: no pictures scraped")
    uploaded_pictures = upload_post_images(picture_urls, selenium_driver)
    if not any(pic.get("s3_url") for pic in uploaded_pictures):
        raise FastFailException(f"FastFail for post {post_url}: no pictures uploaded to s3")

    video_urls = selenium_driver.get_field_retriever_module_value(
        config.post_information_retriever_module.videos_retriever_module,
        "videos_retriever_module",
    )

    return {
        "organisation_names": [organisation_name] if organisation_name else [],
        "id": post_identifier,
        "scraping_time": datetime.today().strftime("%Y-%m-%d-%H:%M:%S"),
        "url": post_url,
        "title": title,
        "description": description,
        "price": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.price_retriever_module,
            "price_retriever_module",
        ),
        "stock_count": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.stock_retriever_module,
            "stock_retriever_module",
        ),
        "vendor": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.vendor_retriever_module,
            "vendor_retriever_module",
        ),
        "poster_link": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.poster_link_retriever_module,
            "poster_link_retriever_module",
        ),
        "posting_time": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.date_retriever_module,
            "date_retriever_module",
        ),
        "location": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.location_retriever_module,
            "location_retriever_module",
        ),
        "ships_from": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.ships_from_retriever_module,
            "ships_from_retriever_module",
        ),
        "ships_to": selenium_driver.get_field_retriever_module_value(
            config.post_information_retriever_module.ships_to_retriever_module,
            "ships_to_retriever_module",
        ),
        "pictures": uploaded_pictures,
        "videos": video_urls,
        "archive_link": selenium_driver.take_webshot() if take_screenshot else None,
        "alternate_links": selenium_driver.get_alternate_links(),
    }


def upload_post_images(picture_urls: List[str], selenium_driver: Selenium) -> list:
    """Fetch post images from the driver requests and upload them to s3

    Returns:
        list of image dict ({"picture_url": "", "s3_url": ""})
    """
    pictures = []
    for picture_url in list(set(picture_urls)):
        is_blacklisted_image = False
        s3_url = None
        try:
            s3_url, is_blacklisted_image = upload_post_image(picture_url, selenium_driver)
        except Exception as e:
            logger.warn(
                f"Upload of post image {picture_url} to s3 failed. Trying to upload from url. Exception {repr(e)}"
            )
        # skip blacklisted images
        if is_blacklisted_image:
            logger.info(f"Image {picture_url} skipped as it is not valid")
        else:
            pictures.append({"picture_url": picture_url, "s3_url": s3_url})

    return pictures


def upload_post_image(picture_url: str, selenium_driver: Selenium) -> str:
    request_id = selenium_driver.get_request_id_for_url(picture_url)
    if not request_id:
        logger.warn(f"Failed to get request id for {picture_url}, trying to open the image")
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("picture_url", picture_url)
            sentry_sdk.capture_message("Failure to get image from request_id")
        s3_url, is_blacklisted_image = upload_image_from_url(picture_url)
        if s3_url:
            return s3_url, is_blacklisted_image
        logger.warn(f"Failed to get upload image with requests: {picture_url}")

        # FIXME: 2023-08-30 by Dana, temporary reduce load on proxies
        raise RuntimeError("Image upload from a new tab is not implemented for the moment.")

        main_tab = selenium_driver.driver.current_window_handle
        selenium_driver.driver.switch_to.new_window("tab")
        selenium_driver.driver.get(picture_url)
        time.sleep(1)

        request_id = selenium_driver.get_request_id_for_url(picture_url)

        try:
            img = selenium_driver.get_img_bytes_from_request_id(request_id) if request_id else None
        except Exception:
            img = None

        selenium_driver.driver.close()
        selenium_driver.driver.switch_to.window(main_tab)

        if not img:
            raise RuntimeError(f"Failed to open image for {picture_url}")

    else:
        img = selenium_driver.get_img_bytes_from_request_id(request_id)

    return upload_image_from_bytes(img)


def scrape_instagram_posts(
    post_identifier_to_light_post: Dict[str, BasePost],
    concurrency: int = 8,
    upload_request_id: str = None,
    post_identifier_upload_id_mapping: dict = None,
):
    """Retrieve the posts published on Instagram corresponding to a list of hashtags using hashtag search

    Parameters:
    ===========
    post_identifier_to_light_post: Dict[str, BasePost],
    concurrency: int
    upload_request_id: str or None
    post_identifier_upload_id_mapping: dict or None
        mapping between the shortcodes and their upload ID

    Returns:
    ========
    posts: dict
        {shortcode: post_content}
    """

    query_time = datetime.now(timezone.utc)

    logger.info(f"Scraping {len(post_identifier_to_light_post)} posts ({concurrency} by {concurrency})...")

    shortcodes = list(post_identifier_to_light_post.keys())
    with ThreadPool(concurrency) as p:
        posts = tqdm(p.imap(get_post_multithreading, shortcodes, chunksize=8), total=len(shortcodes))

        # For now, we don't handle posts which are just a video (we handle carousel posts which contain both pictures and videos though)
        posts_list = [post for post in posts if post and post.get("pictures")]

    scraped_posts = dict()
    for post_details in posts_list:
        shortcode = post_details["shortcode"]

        # Add the query time to the post details
        post_details.update({"query_time": query_time.strftime("%Y-%m-%d_%H-%M-%S")})

        scraped_posts[shortcode] = post_details

        search_query_tag = (
            [f"search_query:{post_identifier_to_light_post[shortcode].search_query}"]
            if post_identifier_to_light_post[shortcode].search_query
            else []
        )
        if post_identifier_to_light_post[shortcode]:
            scraped_posts[shortcode]["light_post_payload"] = post_identifier_to_light_post[shortcode].serialize
            scraped_posts[shortcode]["tags"] = post_identifier_to_light_post[shortcode].tags + search_query_tag
            scraped_posts[shortcode]["skip_filter_scraped_results"] = post_identifier_to_light_post[
                shortcode
            ].skip_filter_scraped_results
            scraped_posts[shortcode]["valid_organisations"] = post_identifier_to_light_post[
                shortcode
            ].valid_organisations

    # Set URL upload status to failed for failed upload requests
    if upload_request_id:
        scraped_shortcodes = set(scraped_posts.keys())
        for shortcode in set(post_identifier_to_light_post.keys()):
            status = "ended" if shortcode in scraped_shortcodes else "failed"
            redis_DAO.set_url_upload_status(upload_request_id, post_identifier_upload_id_mapping[shortcode], status)
            logger.info(f"{shortcode} status is '{status}'")

    return scraped_posts


def scrape_instagram_posts_from_usernames(usernames: List[str]) -> List[BasePost]:
    """Retrieve the posts published on Instagram by usernames"""

    all_light_posts = []
    for username in list(set(usernames)):
        all_light_posts += get_profile_posts(username)

    return all_light_posts
