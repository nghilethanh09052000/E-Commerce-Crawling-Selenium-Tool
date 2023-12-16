import json
import traceback
from collections import defaultdict
from datetime import datetime, timezone

from app import logger
from app.dao import RedisDAO, TaskDAO, OrganisationDAO
from app.helpers.navee_driver import get_url_data
from app.models.enums import DataSource, ScrapingType, UrlPageType
from app.scrapers import FacebookScraper, InstagramScraper, MarketplaceScraper

from app.scrapers.helpers import get_scraper_module
from app.service.scrape import scrape
from app.settings import sentry_sdk


task_DAO = TaskDAO()
redis_DAO = RedisDAO()
organisation_DAO = OrganisationDAO()


def scrape_posts_by_domain_keywords(
    search_queries,
    domain_name,
    scraping_type=ScrapingType.POST_SEARCH_COMPLETE,
    organisation_name=None,
    enable_logging=False,
):
    return scrape(
        scraper_module=MarketplaceScraper,
        domain_name=domain_name,
        search_queries=search_queries,
        scraping_type=scraping_type,
        organisation_name=organisation_name,
        enable_logging=enable_logging,
    )


def scrape_by_task_id(task_id, enable_logging=False):
    """launch scraping task by task id"""

    logger.info(f"Running task {task_id}")

    task = task_DAO.get(task_id)

    if not task:
        logger.info(f"No task with ID {task_id}")
        exit()

    task_DAO.update(task_id, {"last_run_time": datetime.now(timezone.utc)})

    if task.search_queries:
        search_queries = task.search_queries
    else:
        search_queries = organisation_DAO.get_organisation_localized_keywords(
            organisation_id=task.organisation.id,
            country_code=task.website.country_code,
            include_main_queries=True,
        )

    domain_name = task.website.name
    scraping_type = ScrapingType.POST_SEARCH_COMPLETE if task.scraping_type is None else task.scraping_type
    config_file = task.config_file or domain_name

    scraper_module, source = get_scraper_module(
        domain_name, config_file=config_file, scraping_type=ScrapingType.POST_SEARCH_COMPLETE
    )
    if domain_name in ["instagram.com"] and task.config_file not in ["smelter.ai"]:
        if task.config_file == "instagram_hashtag_search":
            scraping_type = ScrapingType.POST_SEARCH_COMPLETE
        elif task.config_file in ["instagram_radarly"]:
            scraping_type = ScrapingType.POST_SEARCH_RADARLY
        else:
            raise ValueError(f"Unsupported config file for social media tasks: {task.config_file}")

    scrape(
        scraper_module=scraper_module,
        scraping_type=scraping_type,
        domain_name=domain_name,
        search_queries=search_queries,
        organisation_name=None if not task.organisation else task.organisation.name,
        send_to_counterfeit_platform=task.send_posts_to_counterfeit_platform,
        task_id=task.id,
        config_file=config_file,
        enable_logging=enable_logging,
        max_posts_to_browse=task.max_posts_to_browse,
        max_posts_to_discover=task.max_posts_to_discover,
        sample=True,
        skip_search_filter=False,
        source=source,
        search_image_urls=task.search_image_urls,
    )


def scrape_posts_by_domain_name(domain_name, enable_logging=False):
    """Scrape cached list of post urls to scrape for each organisation"""

    logger.input(f"Start scrape_posts_by_domain_name {domain_name}")

    posts = redis_DAO.get_posts_to_scrape_by_domain(domain_name)

    # Get posts by organisations
    posts_by_organisation = defaultdict(list)
    for post in posts:
        posts_by_organisation[post["organisation_name"]].append(post)

    scraper_module, _ = get_scraper_module(domain_name)

    for organisation, posts in posts_by_organisation.items():
        # Read from the post objects whether to scrape posts even if they already exist for the same organisation (useful for price monitoring)
        rescrape_existing_posts = True if any([post.get("rescrape_existing_posts") for post in posts]) else False

        ## TODO: this will be obeselete once we implement this domain in the endpoint scraping
        if domain_name == "instagram.com":
            post_identifiers = [
                post.get("url").split("/p/")[1].split("/")[0]
                for post in posts
                if post.get("url") and "/p/" in post.get("url")
            ]
            # Scrape posts
            params = {
                "scraper_module": scraper_module,
                "domain_name": domain_name,
                "organisation_name": organisation,
                "send_to_counterfeit_platform": True,
                "post_urls": post_identifiers,
                "scraping_type": ScrapingType.POST_SCRAPE_FROM_LIST,
                "source": DataSource.RISE_RECRAWLING,
                "rescrape_existing_posts": rescrape_existing_posts,
                "enable_logging": enable_logging,
            }
            try:
                scrape(**params)
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error(f"Scraping failed, params: {params}")
                sentry_sdk.capture_exception(e)
        else:
            for post in posts_by_organisation[organisation]:
                url = post["url"] if "post" not in post else post["post"]["url"]
                logger.info(f"Call endpoint to scrape {url}")
                body = {
                    "url": url,
                    "enable_logging": enable_logging,
                    "source": DataSource.RISE_RECRAWLING.name,
                    "scraping_type": ScrapingType.POST_SCRAPE_FROM_LIST.name,
                    "send_to_counterfeit_platform": True,
                    "rescrape_existing_posts": rescrape_existing_posts,
                    "organisation_name": organisation,
                    "page_type": UrlPageType.POST.name,
                }
                logger.info(f"API request: {body}")
                try:
                    # getting data also sends data to the insertion worker
                    url_data = get_url_data(body=body)
                except Exception as e:
                    logger.error(f"Driver API call for scraping failed. body: {str(body)} | {repr(e)}")
                    sentry_sdk.capture_exception(e)
                    continue
                logger.info(f"API response: {url_data}")
                if url_data and url_data.get("successful"):
                    logger.info(f"Successful scraping {url}")
                else:
                    logger.info(f"Unsuccessful scraping {url}")
                    with sentry_sdk.push_scope() as scope:
                        scope.set_extra("Scraped URL", url)
                        sentry_sdk.capture_message("Unsuccessful Post Scraping")

    logger.output(f"Completed scrape_posts_by_domain_name {domain_name}")


def scrape_posts_by_batch_key(upload_batch_key, send_to_counterfeit_platform, enable_logging=False):
    logger.info(f"Running posts batch upload {upload_batch_key}")
    batch = json.loads(redis_DAO.get(upload_batch_key))
    logger.info(f"Batch {upload_batch_key} : {str(batch)}")
    posts = batch["posts"]
    organisation_name = batch["organisation_name"]
    upload_request_id = batch["upload_request_id"]
    domain_name = batch["domain_name"]
    scraper_module, _ = get_scraper_module(domain_name)

    if domain_name == "instagram.com":
        for post in posts:
            try:
                url = post["url"]
                post["post_identifier"] = url.split("/p/")[1].split("/")[0]
                post_identifier_url_mapping = {post["post_identifier"]: url}
                post_identifier_upload_id_mapping = {post["post_identifier"]: post["upload_id"]}
                logger.info(f"Start scraping {url}")
                redis_DAO.set_url_upload_status(upload_request_id, post["upload_id"], "started")
                _, scraped_posts, _ = scrape(
                    scraper_module=scraper_module,
                    domain_name=domain_name,
                    scraping_type=ScrapingType.POST_SCRAPE_FROM_LIST,
                    organisation_name=organisation_name,
                    source=DataSource.MANUAL_INSERTION,
                    post_urls=list(post_identifier_url_mapping.keys()),
                    rescrape_existing_posts=True,
                    skip_search_filter=True,
                    screenshot_posts=True,
                    screenshot_profiles=True,
                    send_to_counterfeit_platform=send_to_counterfeit_platform,
                    upload_posts_batch=posts,  # useful to get the tags, label and upload_id
                    upload_request_id=upload_request_id,  # useful to set the URL upload status
                    post_identifier_url_mapping=post_identifier_url_mapping,  # useful to send the proper URL to the Insertion Worker
                    post_identifier_upload_id_mapping=post_identifier_upload_id_mapping,  # useful to set the proper status key to the Insertion Worker
                    enable_logging=enable_logging,
                )
                assert scraped_posts, "no result from 'scrape'"
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.info(f"Scraping failed {url}")
                redis_DAO.set_url_upload_status(upload_request_id, post["upload_id"], "failed")
                sentry_sdk.capture_exception(e)
            logger.info(f"Completed scraping {url}")
    else:
        for post in posts:
            url = post["url"] if "post" not in post else post["post"]["url"]
            logger.info(f"Call endpoint to scrape {url}")
            redis_DAO.set_url_upload_status(upload_request_id, post["upload_id"], "started")
            body = {
                "url": url,
                "enable_logging": enable_logging,
                "source": DataSource.MANUAL_INSERTION.name,
                "scraping_type": ScrapingType.POST_SCRAPE_FROM_LIST.name,
                "send_to_counterfeit_platform": send_to_counterfeit_platform,
                "organisation_name": organisation_name,
                "rescrape_existing_posts": True,
                "upload_post": post,
                "upload_request_id": upload_request_id,
                "upload_id": post["upload_id"],
                "page_type": UrlPageType.POST.name,
            }
            try:
                url_data = get_url_data(body=body)
            except Exception as e:
                logger.error(f"Driver API call for scraping failed. body: {str(body)} | {repr(e)}")
                redis_DAO.set_url_upload_status(upload_request_id, post["upload_id"], "failed")
                sentry_sdk.capture_exception(e)
                continue
            logger.info(f"Completed scraping {url}")
            upload_status = status_from_response(url_data)
            redis_DAO.set_url_upload_status(upload_request_id, post["upload_id"], upload_status)
            logger.info(
                f"Upload status {url} : {upload_status}{' (not send to insertion)' if upload_status == 'ended' else ''}"
            )
    logger.info(f"Finished posts batch upload {upload_batch_key}")
    redis_DAO.delete_by_key(upload_batch_key)


def scrape_accounts_by_batch_key(upload_batch_key, send_to_counterfeit_platform, enable_logging=False):
    logger.info(f"Running accounts batch upload {upload_batch_key}")
    batch = json.loads(redis_DAO.get(upload_batch_key))
    logger.info(f"Batch {upload_batch_key} : {str(batch)}")
    accounts = batch["accounts"]
    organisation_name = batch["organisation_name"]
    domain_name = batch["domain_name"]
    upload_request_id = batch["upload_request_id"]

    if domain_name == "instagram.com":
        for account in accounts:
            try:
                url = account["url"]
                account["username"] = url.split("instagram.com/")[1].split("/")[0]
                usernames = [account["username"]]
                account_identifier_url_mapping = {account["username"]: url}
                logger.info(f"Start scraping {url}")
                redis_DAO.set_url_upload_status(upload_request_id, account["upload_id"], "started")
                _, _, scraped_posters = scrape(
                    scraper_module=InstagramScraper,
                    scraping_type=ScrapingType.POSTER_SEARCH,
                    domain_name=domain_name,
                    organisation_name=organisation_name,
                    scrape_poster_posts=False,
                    rescrape_existing_profiles=True,
                    skip_search_filter=True,
                    screenshot_profiles=True,
                    usernames=usernames,
                    upload_accounts_batch=accounts,
                    upload_request_id=upload_request_id,
                    upload_account_identifier_url_mapping=account_identifier_url_mapping,
                    send_to_counterfeit_platform=send_to_counterfeit_platform,
                    enable_logging=enable_logging,
                )
                assert scraped_posters, "no result from 'scrape'"
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.info(f"Scraping failed {url}")
                redis_DAO.set_url_upload_status(upload_request_id, account["upload_id"], "failed")
                sentry_sdk.capture_exception(e)
            logger.info(f"Completed scraping {url}")
    else:
        for account in accounts:
            try:
                url = account["url"]
                urls = {url: None}
                upload_account_identifier_url_mapping = {url: account["upload_id"]}
                logger.info(f"Start scraping {url}")
                redis_DAO.set_url_upload_status(upload_request_id, account["upload_id"], "started")
                _, _, scraped_posters = scrape(
                    scraper_module=MarketplaceScraper,
                    domain_name=domain_name,
                    organisation_name=organisation_name,
                    send_to_counterfeit_platform=send_to_counterfeit_platform,
                    scraping_type=ScrapingType.POSTER_SEARCH,
                    scrape_poster_posts=False,
                    rescrape_existing_profiles=True,
                    poster_urls=urls,
                    upload_accounts_batch=accounts,
                    upload_request_id=upload_request_id,
                    upload_account_identifier_url_mapping=upload_account_identifier_url_mapping,
                    enable_logging=enable_logging,
                )
                assert scraped_posters, "no result from 'scrape'"
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.info(f"Scraping failed {url}")
                redis_DAO.set_url_upload_status(upload_request_id, account["upload_id"], "failed")
                sentry_sdk.capture_exception(e)
            logger.info(f"Completed scraping {url}")
    logger.info(f"Finished accounts batch upload {upload_batch_key}")
    redis_DAO.delete_by_key(upload_batch_key)


def recrawl_instagram_profiles_batch(batch_key):
    logger.info(f"Running IG users batch {batch_key}")

    # Get the batch from Redis
    batch = json.loads(redis_DAO.get(batch_key))

    try:
        usernames = [user["username"] for user in batch]

        scrape(
            scraper_module=InstagramScraper,
            domain_name="instagram.com",
            scraping_type=ScrapingType.POSTER_SEARCH,
            scrape_poster_posts=True,
            usernames=usernames,
            rescrape_existing_profiles=True,
            skip_search_filter=True,
            concurrency=1,
        )

    except Exception as e:
        logger.warn("Exception on scrape")
        logger.warn(traceback.format_exc())
        sentry_sdk.capture_exception(e)

    # Delete the Redis batch now that it has been handled
    redis_DAO.delete_by_key(batch_key)


def scrape_poster(
    poster_url,
    website_name,
    scrape_poster_posts=False,
    send_to_counterfeit_platform=False,
    enable_logging=False,
):
    logger.info(f"Running Scrape for poster {poster_url} from domain {website_name}")

    if website_name == "instagram.com":
        scraper_module = InstagramScraper
    elif website_name == "facebook.com":
        scraper_module = FacebookScraper
    else:
        scraper_module = MarketplaceScraper

    scrape(
        scraper_module=scraper_module,
        domain_name=website_name,
        poster_urls={poster_url: None},
        send_to_counterfeit_platform=send_to_counterfeit_platform,
        scrape_poster_posts=scrape_poster_posts,
        scraping_type=ScrapingType.POSTER_SEARCH,
        enable_logging=enable_logging,
        scrape_search_results=True,
        skip_search_filter=True,
    )


def status_from_response(url_data):
    status = "failed"
    try:
        pages = url_data.get("pages")
        assert pages, "Pages are expected in response"
        page = pages[0]
        post = page.get("post")
        assert post, f"Lack of 'post' in 'page' means exception during scraping. {page}"
        status = "ended"
        payload = post[0].get("payload")
        assert payload, "Payload are expected in response"
        if payload.get("sent_to_insertion"):
            status = "sent_to_insertion"
    except Exception as e:
        logger.error(f"Driver respose indicates scraping fail. {repr(e)}")
    return status
