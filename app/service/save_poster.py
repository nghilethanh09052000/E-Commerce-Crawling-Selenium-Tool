from tqdm import tqdm
from datetime import datetime

from app import logger

from app.dao import OrganisationDAO, WebsiteDAO, RedisDAO, PosterDAO

from app.settings import sentry_sdk

from app.service.send import send_profile_insertion_task
from app.service.validate_images import filter_valid_pictures_module

organisation_DAO = OrganisationDAO()
website_DAO = WebsiteDAO()
redis_DAO = RedisDAO()
poster_DAO = PosterDAO()


def save_poster(
    posters,
    domain_name,
    send_to_counterfeit_platform,
    accounts_batch=None,
    upload_request_id=None,
    organisation_name=None,
):
    if accounts_batch is None:
        accounts_batch = []
    # Build a dictionary account URL: account upload request object
    url_account_upload_request_mapping = {account_request["url"]: account_request for account_request in accounts_batch}

    geo_map = dict()
    for account_request in accounts_batch:
        url = account_request.get("url")
        geo = account_request.get("geo")
        if url and geo:
            geo_map[url] = geo

    saved_posters = []
    website = website_DAO.get(domain_name)

    for poster in tqdm(posters):
        logger.info(f"Found poster {poster['url']}: {poster}")

        try:
            # keep only valid pictures
            filtered_pictures = None
            if not poster.get("profile_pic_url"):
                filtered_pictures = filter_valid_pictures_module(poster["profile_pic_url"])

            poster["profile_pic_url"] = None if not filtered_pictures else filtered_pictures[0]

            account_upload_request = url_account_upload_request_mapping.get(poster["id"], dict())

            # Check if poster has to be saved
            if not poster_required_fields_missing(poster):
                # Get poster if exists or create it
                new_poster = create_poster_object(website, poster)
                if send_to_counterfeit_platform:
                    send_profile_insertion_task(
                        new_poster,
                        account_tags=account_upload_request.get("tags", []),
                        account_label=account_upload_request.get("label"),
                        upload_id=account_upload_request.get("upload_id"),
                        upload_request_id=upload_request_id,
                        organisation_name=organisation_name,
                        geo=geo_map.get(poster.get("url")),
                    )
                    saved_posters.append(new_poster)
                    if upload_request_id:
                        redis_DAO.set_url_upload_status(
                            upload_request_id, account_upload_request["upload_id"], "sent_to_insertion"
                        )
            else:
                logger.info(f"poster_required_fields_missing {poster.get('url')}")
                if upload_request_id:
                    redis_DAO.set_url_upload_status(upload_request_id, account_upload_request["upload_id"], "failed")
        except Exception as ex:
            logger.info(f"Error on Poster saving {ex}")
            sentry_sdk.capture_exception(ex)

    logger.info(f"found {len(posters)} posters")

    if len(saved_posters) > 0:
        poster_DAO.bulk_update_posters_in_db(saved_posters)

    return saved_posters


def create_poster_object(website, poster):
    poster_obj = poster_DAO.get_poster(
        website_id=website.id,
        poster_url=poster.get("url"),
        name=poster["name"],
        auto_create=True,
    )

    scraping_time = datetime.today().strftime("%Y-%m-%d-%H:%M:%S")
    poster = {
        "id": poster_obj.id,
        "website_id": website.id,
        "name": poster["name"],
        "scraping_time": poster.get("scraping_time", scraping_time),
        "url": poster["url"],
        "description": poster["description"],
        "profile_pic_url": poster["profile_pic_url"],
        "payload": poster["payload"],
        "archive_link": poster["archive_link"],
    }
    return poster


def poster_required_fields_missing(poster):
    """Return True if the post under examination doesn't have all the fields required, else False"""

    # Check whether a required field is missing
    if not poster["url"] or (
        not poster["description"]
        and not poster["profile_pic_url"]
        and not poster["payload"]
        and not poster["name"]
        and not poster["followers_count"]
    ):
        # One or several required fields are missing
        return True

    return False


def create_or_update_instagram_profiles(scraped_posters):
    instagram = website_DAO.get("instagram.com")

    saved_posters = dict()
    for profile in scraped_posters.values():
        username = profile["username"]

        saved_profile = poster_DAO.upsert_profile(
            username,
            website=instagram,
            description=profile["biography"],
            url=f"https://www.instagram.com/{username}/",
            profile_pic_url=profile["profile_pic_url"],
            posts_count=profile["posts_count"],
            followers_count=profile["followers_count"],
            poster_website_identifier=profile["user_id"],
        )

        saved_posters[username] = saved_profile

    return saved_posters
