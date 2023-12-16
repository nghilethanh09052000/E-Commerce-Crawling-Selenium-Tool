import math
from datetime import datetime, timezone
from typing import Tuple

from tqdm import tqdm

from app import logger, sentry_sdk
from app.models import Website, Organisation
from app.models.enums import DataSource
from app.dao import OrganisationDAO, PostDAO, PosterDAO, WebsiteDAO
from app.service.send import send_insertion_task_with_all_options
from app.service.validate_images import filter_valid_pictures_module

post_DAO = PostDAO()
organisation_DAO = OrganisationDAO()
website_DAO = WebsiteDAO()
poster_DAO = PosterDAO()


def send_posts(
    posts,
    website,
    send_to_counterfeit_platform,
    override_save,
    post_tags,
    search_queries=None,
    task_id=None,
    **args,
):
    # Group posts by organisation_name
    organisation_posts = {}
    for post in posts:
        organisation_names = post.get("organisation_names")
        if not organisation_names:
            organisation_names = ["no_organisation"]
        for organisation_name in organisation_names:
            organisation_posts.setdefault(organisation_name, []).append(post)

    for organisation_name in organisation_posts:
        send_posts_for_org(
            organisation_name=None if organisation_name == "no_organisation" else organisation_name,
            posts=organisation_posts[organisation_name],
            website=website,
            send_to_counterfeit_platform=send_to_counterfeit_platform,
            search_queries=search_queries,
            override_save=override_save,
            post_tags=post_tags,
            task_id=task_id,
            **args,
        )


def send_posts_for_org(
    organisation_name,
    posts,
    website: Website,
    send_to_counterfeit_platform: bool,
    source: DataSource = None,
    post_tags=[],
    override_save=False,
    task_id=None,
    **args,  # TODO: unpack *args
):
    """
    Config options:
        - source (optional): the value to specify in the "source" field of the Counterfeit Platform interface
        - recrawl_ig_images (optional): whether to call the Russian Radarly to get all the post images, default False
    """

    if not organisation_name:
        for post in posts:
            logger.warn(
                f"Found post {post['url']} without organisation {post}",
                post_link=post["url"],
            )

        return

    # Load the batch - provided when handling automated uploads of posts
    upload_posts_batch = args.get("upload_posts_batch", dict()) or dict()
    upload_request_id = args.get("upload_request_id")
    post_identifier_url_mapping = args.get("post_identifier_url_mapping", dict()) or dict()

    # Build a dictionary post URL: post upload request object
    url_post_upload_request_mapping = {
        post_identifier_url_mapping[post_request["post_identifier"]]: post_request
        for post_request in upload_posts_batch
        if "post_identifier" in post_request
    }

    organisation = organisation_DAO.get(organisation_name=organisation_name)
    # check the posts quota for the organisation organisation_name
    max_posts_by_month, posts_sent_this_month = count_posts_sent_this_month(organisation)

    for post in tqdm(posts):
        logger.info(f"Found post {post['url']} for organisation {organisation_name}")

        try:
            logger.info("Start filter_valid_pictures_module")

            # Keep only the valid pictures
            if post["pictures"]:
                # Images with s3 urls don't need to be validated
                valid_urls = [
                    picture["picture_url"] for picture in post["pictures"] if picture.get("s3_url", None) is not None
                ]
                # Validate the pictures with no s3 link associated to them
                valid_urls.extend(
                    filter_valid_pictures_module(
                        [
                            picture["picture_url"]
                            for picture in post["pictures"]
                            if picture["picture_url"] not in valid_urls
                        ]
                    )
                )
                # keep the valid downloadable images only
                post["pictures"] = [picture for picture in post["pictures"] if picture["picture_url"] in valid_urls]

            logger.info(f"END filter_valid_pictures_module with {len(post['pictures'])} pictures")

            # When the post is associated with an upload request, we don't check the number of posts sent
            # and only consider the fields url, scraping_time and price as required
            minimal_required_fields_check = upload_request_id is not None
            if not override_save and (
                not send_to_counterfeit_platform
                or not post_should_be_saved(
                    post, website, posts_sent_this_month, max_posts_by_month, minimal_required_fields_check
                )
            ):
                logger.info(
                    f"Post should NOT be saved. send_to_counterfeit_platform: {send_to_counterfeit_platform}, url: {post.get('url')}"
                )
                continue

            new_post = serialize_post_object(organisation, website, post, task_id)

            logger.info(f"Start sending new post {new_post}")

            if send_to_counterfeit_platform:
                post_url = post["url"]

                # Make sure to retrieve the proper URL if a upload request is being processed
                if post_identifier_url_mapping.get(post["id"]):
                    post_url = post_identifier_url_mapping[post["id"]]

                post_upload_request = url_post_upload_request_mapping.get(post_url, dict())

                send_insertion_task_with_all_options(
                    post=post,
                    organisation_name=organisation_name,
                    post_source=source.name,
                    post_tags=(post_upload_request.get("tags", []) + post_tags),
                    post_label=post_upload_request.get("label"),
                    upload_id=post_upload_request.get("upload_id"),
                    upload_request_id=upload_request_id,
                )

                post_DAO.set_post_as_sent(
                    platform_id=post["id"],
                    organisation_name=organisation.name,
                    domain_name=website.domain_name,
                )
                posts_sent_this_month += 1

                # For upload
                post["sent_to_insertion"] = True

                logger.info(f"Post sent for insertion: {post}")

        except Exception as ex:
            logger.info(f"Error on Post saving {ex}")
            sentry_sdk.capture_exception(ex)

    send_monthly_usage_alert(organisation, posts_sent_this_month, max_posts_by_month)


def count_posts_sent_this_month(organisation: Organisation) -> Tuple[int, int]:
    # Check posts quota for organisation
    max_posts_by_month = organisation.max_posts_to_counterfeit_platform_by_month

    # If max_posts_by_month not set, we allow an infinite number of posts sent to counterfeit platform
    if max_posts_by_month is None:
        return math.inf, 0

    posts_sent_this_month = post_DAO.count_posts_sent_this_month(organisation_id=organisation.id)

    return max_posts_by_month, posts_sent_this_month


def serialize_post_object(organisation, website, post, task_id):
    scraping_time = datetime.now(timezone.utc)
    try:
        scraping_time = datetime.strptime(post["scraping_time"], "%Y-%m-%d-%H:%M:%S")
    except Exception as ex:
        logger.info("Error Parsing Scraping Time Resolve to default scraping time")
        sentry_sdk.capture_message(ex)

    return {
        "organisation_id": organisation.id,
        "website_id": website.id,
        "platform_id": post["id"],
        "scraping_time": scraping_time,
        "url": post["url"],
        "title": post["title"],
        "description": post["description"],
        "price": post["price"],
        "stock_count": post.get("stock_count"),
        "vendor": post["vendor"],
        "pictures": [picture["picture_url"] for picture in post["pictures"]],
        "videos": post.get("videos"),
        "archive_link": post.get("archive_link"),
        "poster_link": post.get("poster_link"),
        "location": post.get("location"),
        "ships_from": post.get("ships_from"),
        "ships_to": post.get("ships_to"),
        "posting_time": post.get("posting_time"),
        "light_post_payload": post.get("light_post_payload"),
        "task_id": task_id,
        "risk_score": post.get("risk_score"),
        "tags": post.get("tags"),
        "skip_filter_scraped_results": post.get("skip_filter_scraped_results"),
    }


def create_new_json_post(organisation, website, post, search_queries):
    new_post = {
        "organisation": organisation,
        "website": website.serialize,
        "search_queries": search_queries,
        "platform_id": post["id"],
        "scraping_time": post["scraping_time"],
        "url": post["url"],
        "title": post["title"],
        "description": post["description"],
        "price": post["price"],
        "vendor": post["vendor"],
        "stock_count": post["stock_count"] if post.get("stock_count") else None,
        "poster_link": post["poster_link"] if post.get("poster_link") else None,
        "location": post["location"] if post.get("location") else None,
        "ships_from": post["ships_from"] if post.get("ships_from") else None,
        "ships_to": post["ships_to"] if post.get("ships_to") else None,
        "posting_time": post["posting_time"] if post.get("posting_time") else None,
        "pictures": [picture["picture_url"] for picture in post["pictures"]],
        "videos": post["videos"],
        "archive_link": post.get("archive_link"),
    }

    return new_post


def post_should_be_saved(post, website, posts_nb, max_posts_nb, minimal_required_fields_check=False):
    """Determine whether the post has all the required fields and the organisation's quota has not been reached"""

    required_fields = ["url", "scraping_time"]

    if minimal_required_fields_check:
        # If minimal_required_fields_check is true (typically when the post is associated with an upload request),
        # we don't check the number of posts sent and only consider the fields url, scraping_time and price as required
        required_fields += ["pictures"]

    else:
        extra_required_fields = [
            [website.vendor_required, "vendor"],
            [website.title_required, "title"],
            [website.pictures_required, "pictures"],
            [website.description_required, "description"],
        ]
        required_fields += [field for condition, field in extra_required_fields if condition]

        if posts_nb >= max_posts_nb:
            logger.info(
                f"Post not saved because the organisation's quota has been reached {posts_nb} >= {max_posts_nb}: {post}"
            )
            return False

    for field in required_fields:
        if not post[field]:
            logger.info(f"Post not saved because it does not have the required field '{field}': {post}")
            return False

    return True


def send_monthly_usage_alert(organisation, posts_sent_this_month, max_posts_by_month):
    """Send a Sentry alert if the number of posts sent this month for this organisation has reached a certain threshold"""

    # Sentry alert about monthly usage
    if max_posts_by_month != math.inf:
        if posts_sent_this_month in [int(max_posts_by_month * percentage) for percentage in [0.5, 0.75, 0.9]]:
            sentry_sdk.capture_message(
                "Organisation {} reached {}% of its monthly quota".format(
                    organisation.name,
                    int(100 * posts_sent_this_month / max_posts_by_month),
                )
            )


def create_or_update_instagram_posts(scraped_posts, organisation_name, task_id):
    organisation = organisation_DAO.get(organisation_name)

    saved_posts = dict()

    if scraped_posts:
        for post in scraped_posts.values():
            query_time = datetime.strptime(post["query_time"], "%Y-%m-%d_%H-%M-%S")
            post_object = post_DAO.create_or_update_instagram_post(post, organisation, query_time, task_id=task_id)
            saved_posts[post["shortcode"]] = {
                "post_object": post_object,
                "tags": post.get("tags"),
                "skip_filter_scraped_results": post.get("skip_filter_scraped_results"),
                "valid_organisations": post.get("valid_organisations"),
            }

    return saved_posts
