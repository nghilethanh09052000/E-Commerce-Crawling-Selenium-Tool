import json
from datetime import datetime, timezone
import ast

from tqdm import tqdm

from app import logger
from app.settings import (
    COUNTERFEIT_PLATFORM_INSERTION_QUEUE,
    SCRAPING_QUEUE,
    ENVIRONMENT_NAME,
    sqs_client,
    sqs_client_scraping,
)
from app.models import Post
from app.models.enums import DataSource
from app.dao import PostDAO, RedisDAO

post_DAO = PostDAO()
redis_DAO = RedisDAO()


def send_scraping_task(task):
    task_json = json.dumps(task, sort_keys=True)
    scraping_queue = sqs_client_scraping.get_queue_by_name(QueueName=SCRAPING_QUEUE)
    scraping_queue.send_message(MessageBody=task_json)


def send_insertion_task(post_body):
    if post_body.get("profile"):
        # Log the sending of a profile
        logger.info(
            f"Sending insertion task for poster {post_body['profile']['url']}: {post_body}",
            post_link=post_body["profile"]["url"],
        )
    else:
        # Log the sending of a profile
        logger.info(
            f"Sending insertion task for post {post_body['post']['url']}: {post_body}",
            post_link=post_body["post"]["url"],
        )

    queue = sqs_client.get_queue_by_name(QueueName=COUNTERFEIT_PLATFORM_INSERTION_QUEUE)
    message_response = queue.send_message(MessageBody=json.dumps(post_body))
    logger.info(f"Message Insertion Response: {message_response}")


def send_insertion_task_with_all_options(
    post,
    organisation_name,
    post_source,
    post_tags=[],
    post_label=None,
    upload_id=None,
    upload_request_id=None,
):
    """Send a post to the Counterfeit Platform. "with_all_options" means that we add the image to RISE, search RISE and call all workers

    Args:
        post (dict)
        organisation_name (str)
        post_source (str): the value to specify in the "source" field of the Counterfeit Platform interface
        post_tags (str[]): the value to specify in the "post_tags" field of the Counterfeit Platform interface
        post_label (str): the value to specify in the "post_label" field of the Counterfeit Platform interface
        upload_id (int): the ID of the Upload History object in the Counterfeit Platform
    """

    post_link = post.get("url")

    if post.get("scraping_time"):
        if isinstance(post.get("scraping_time"), str):
            scraping_time = post.get("scraping_time")
        else:
            # post.get('scraping_time') is a datetime object
            scraping_time = datetime.strftime(post.get("scraping_time"), "%Y-%m-%d-%H:%M:%S")

    if isinstance(post.get("posting_time"), str):
        posting_time = post.get("posting_time")

    elif isinstance(post.get("posting_time"), datetime):
        posting_time = datetime.strftime(post.get("posting_time"), "%Y-%m-%d-%H:%M:%S")

    else:
        posting_time = None

    payload = {
        "platform_id": post.get("platform_id"),
        "posting_time": posting_time,
        "poster_link": post.get("poster_link"),
        "location": post.get("location"),
        "ships_from": post.get("ships_from"),
        "ships_to": post.get("ships_to"),
    }

    # If this point has been reached, then the post is valid for being sent to the Counterfeit Platform
    post_to_send = {
        "environment_name": ENVIRONMENT_NAME,
        "organisation_name": organisation_name,
        "add_image_to_rise": True,
        "search_in_rise": True,
        "launch_archiving": True,
        "launch_classifying": True,
        "launch_logo_detection": True,
        "launch_metadata": True,
        "post": {
            "scraping_time": scraping_time,
            "poster": post.get("vendor") if post.get("vendor") else post.get("poster"),
            "poster_url": post.get("poster_url"),
            "price": post.get("price"),
            "stock_count": post.get("stock_count"),
            "url": post_link,
            "archive_link": post.get("archive_link"),
            "title": post.get("title"),
            "pictures": post.get("pictures"),
            "videos": post.get("videos"),
            "description": post.get("description"),
            "source": post_source if post_source else DataSource.SPECIFIC_SCRAPER.name,
            "post_tags": post_tags + post.get("tags", []),
            "post_label": post_label,
            "category": None,
            "payload": payload,
            "upload_id": upload_id,
            "upload_request_id": upload_request_id,
            "poster_website_identifier": post.get("poster_website_identifier"),
            "risk_score": post.get("risk_score"),
            "alternate_links": post.get("alternate_links"),
        },
    }

    send_insertion_task(post_body=post_to_send)


def send_profile_insertion_task(
    profile,
    poster_source=DataSource.SPECIFIC_SCRAPER.name,
    organisation_name=None,
    account_tags=[],
    account_label=None,
    upload_url=None,
    upload_id=None,
    upload_request_id=None,
    geo=None,
):
    scraping_time = datetime.strftime(datetime.now(timezone.utc), "%Y-%m-%d-%H:%M:%S")

    profile_to_send = {
        "environment_name": ENVIRONMENT_NAME,
        "organisation_name": organisation_name,
        "profile": {
            "name": profile.get("name"),
            "description": profile.get("description"),
            "url": upload_url
            if upload_url
            else profile.get("url"),  # if the poster URL is provided in an upload request, return the same
            "profile_pic_url": profile.get("profile_pic_url"),
            "payload": profile.get("payload"),
            "archive_link": profile.get("archive_link"),
            "posts_count": profile.get("posts_count"),
            "followers_count": profile.get("followers_count"),
            "scraping_time": scraping_time,
            "source": poster_source,
            "account_tags": account_tags,
            "account_label": account_label,
            "upload_id": upload_id,
            "upload_request_id": upload_request_id,
            "poster_website_identifier": profile.get("poster_website_identifier"),
        },
    }
    if geo:
        profile_to_send["profile"]["geo"] = geo

    send_insertion_task(post_body=profile_to_send)


def send_instagram_posts(
    posts_to_send,
    upload_posts_batch=[],
    upload_request_id=None,
    post_identifier_url_mapping=dict(),
    post_identifier_upload_id_mapping=None,
):
    # Build a dictionary post URL: post upload request object
    url_post_upload_request_mapping = {post_request["url"]: post_request for post_request in upload_posts_batch}

    for post in tqdm(posts_to_send):
        organisation_names = [post["organisation_name"]]
        if "Gucci" in organisation_names:
            organisation_names.append("Gucci_Grey_Market")

        for organisation_name in organisation_names:
            post_obj: Post = post["post_object"]

            upload_url = post_identifier_url_mapping.get(post["shortcode"])
            post_upload_request = url_post_upload_request_mapping.get(upload_url, dict())

            post_dict = {
                "scraping_time": post_obj.scraping_time,
                "poster": post_obj.vendor,
                "poster_url": f"https://www.instagram.com/{post_obj.vendor}",
                "price": post_obj.price,
                "url": post_obj.url,
                "archive_link": post_obj.archive_link,
                "title": post_obj.title,
                "pictures": post_obj.pictures,
                "description": post_obj.description,
                "poster_website_identifier": post_obj.poster_website_identifier,
                "risk_score": ast.literal_eval(post_obj.light_post_payload["risk_score"]).get(organisation_name),
            }

            send_insertion_task_with_all_options(
                post_dict,
                organisation_name,
                "RUSSIAN_RADARLY",
                post_tags=post_upload_request.get("tags", []) + post.get("tags", []),
                post_label=post_upload_request.get("label"),
                upload_id=post_upload_request.get("upload_id"),
                upload_request_id=upload_request_id,
            )

            if post_identifier_upload_id_mapping is not None and post["shortcode"] in post_identifier_upload_id_mapping:
                redis_DAO.set_url_upload_status(
                    upload_request_id, post_identifier_upload_id_mapping[post["shortcode"]], "sent_to_insertion"
                )
                logger.info(f"{post['shortcode']} status is 'sent_to_insertion'")

            post_DAO.set_post_as_sent(
                platform_id=post["shortcode"],
                organisation_name=organisation_name,
                domain_name="instagram.com",
            )


def send_instagram_profiles(
    profiles_to_send,
    organisation_name=None,
    upload_accounts_batch=None,
    upload_request_id=None,
    upload_account_identifier_url_mapping=None,
):
    """Send profile objects to the Counterfeit Platform

    Parameters:
    ===========
    profiles_to_send: dict[]
    upload_accounts_batch: dict[]
        useful to get the tags, label and upload_id to send for insertion
    upload_request_id: int or None
        useful to set the URL upload status if the scraping of an account fails
    upload_account_identifier_url_mapping: dict
        useful to send the original URL to the Insertion Worker
    """

    # Build a dictionary account URL: account upload request object
    if upload_accounts_batch is None:
        upload_accounts_batch = []
    if upload_account_identifier_url_mapping is None:
        upload_account_identifier_url_mapping = dict()
    url_account_upload_request_mapping = {
        account_request["url"]: account_request for account_request in upload_accounts_batch
    }
    geo_map = dict()
    for account_request in upload_accounts_batch:
        username = account_request.get("username")
        geo = account_request.get("geo")
        if username and geo:
            geo_map[username] = geo

    for profile in tqdm(profiles_to_send):
        profile_obj = profile["profile_object"]

        upload_url = upload_account_identifier_url_mapping.get(profile["username"])
        account_upload_request = url_account_upload_request_mapping.get(upload_url, dict())

        profile_dict = {
            "name": profile_obj.name,
            "description": profile_obj.description,
            "url": profile_obj.url,
            "profile_pic_url": profile_obj.profile_pic_url,
            "payload": profile_obj.payload,
            "archive_link": profile_obj.archive_link,
            "posts_count": profile_obj.posts_count,
            "followers_count": profile_obj.followers_count,
            "poster_website_identifier": profile_obj.poster_website_identifier,
        }

        send_profile_insertion_task(
            profile_dict,
            "RUSSIAN_RADARLY",
            organisation_name=organisation_name,
            account_tags=account_upload_request.get("tags", []),
            account_label=account_upload_request.get("label"),
            upload_url=upload_url,
            upload_id=account_upload_request.get("upload_id"),
            upload_request_id=upload_request_id,
            geo=geo_map.get(profile_obj.name),
        )

        if upload_request_id:
            redis_DAO.set_url_upload_status(upload_request_id, account_upload_request["upload_id"], "sent_to_insertion")
            logger.info(f"{profile_obj.url} status is 'sent_to_insertion'")
