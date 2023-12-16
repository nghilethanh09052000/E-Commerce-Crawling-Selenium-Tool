from typing import List, Optional, Tuple
from datetime import datetime
import time

from app import logger, sentry_sdk
from russian_radarly.lambda_interface import (
    QueryType,
    RussianRadarlyException,
    RussianRadarlyTimeout,
    call_russian_radarly,
)
from automated_moderation.dataset import BasePost, BaseImage, BasePoster, BaseWebsite


def get_profile_multithreading(args: Tuple[Optional[str], Optional[int]]):
    """This function is meant to be used in a multiprocessing context"""

    username, user_id = args
    profile_details = get_profile(username, user_id)

    if not profile_details:
        return {}

    return {username: profile_details}


def get_profile(username, user_id=None):
    """Retrieve the biography and profile picture from a username or a user ID (on Instagram, the username can be changed while the user ID can't)

    Args:
        username (str)
        user_id (int)

    Returns:
        profile_details (dict)
    """

    # Get the profile ID
    try:
        if user_id:
            profile = call_russian_radarly(
                QueryType.GET_PROFILE_DETAILS_FROM_USER_ID,
                profile_id=user_id,
                max_attempts=1,
            )
        else:
            profile = call_russian_radarly(QueryType.GET_PROFILE_DETAILS, username=username, max_attempts=1)
    except (RussianRadarlyException, RussianRadarlyTimeout) as e:
        logger.error(repr(e))
        return dict()

    user = profile["user"]

    user_id = int(user["user_id"])
    profile_pic_url = user["profile_pic_url"]
    posts_count = user["posts_count"]
    followers_count = user["followers_count"]

    # Compute the complete biography by appending the user full name and external URL, which can both contain precious insights
    biography = user["full_name"] + "\n\n" + user["biography"]
    if user["external_url"]:
        biography += "\n\n" + user["external_url"]

    profile.update(
        {
            "username": username,
            "user_id": user_id,
            "profile_pic_url": profile_pic_url,
            "biography": biography,
            "posts_count": posts_count,
            "followers_count": followers_count,
        }
    )

    return profile


def get_profile_posts(username: str, max_attempts: int = 5) -> List[BasePost]:
    """Retrieve the posts of an Instagram user"""

    logger.info(f"Retrieving publications from the user {username}...")

    attempts = 0

    # Get the profile ID
    try:
        profile = call_russian_radarly(QueryType.GET_PROFILE_DETAILS, username=username, max_attempts=3)
    except (RussianRadarlyException, RussianRadarlyTimeout):
        return []

    user_id = int(profile["user"]["user_id"])

    page = profile

    light_posts = []

    while page:
        try:

            # The posts are retrieved 12 by 12
            light_posts += [
                BasePost(
                    id=post_dict["shortcode"],
                    images=[BaseImage(url=picture_url) for picture_url in post_dict["pictures"]],
                    poster=BasePoster(id=post_dict["owner"]["id"]),
                    created_at=datetime.strptime(post_dict["publication_datetime"], "%Y-%m-%d %H:%M:%S"),
                    description=post_dict["caption"],
                    search_query=f"from profile:{username}",
                    website=BaseWebsite(domain_name="instagram.com", website_category="Social Media"),
                )
                for post_dict in page["media"]["posts"]
            ]

            # Use print here to have a proper display of the evolution of the scraping when running locally
            # Not meaningful for logging though, and logging does not handle the argument "end" which is used to print the line of text in place of the previous one
            print(f" -> {len(light_posts)} shortcodes retrieved so far", end="\r")

            end_cursor = page["media"]["page_info"]["end_cursor"]
            has_next_page = page["media"]["page_info"]["has_next_page"]

            if has_next_page:

                time.sleep(1)

                page = call_russian_radarly(
                    QueryType.GET_PROFILE_POSTS,
                    profile_id=user_id,
                    end_cursor=end_cursor,
                    max_attempts=3,
                )
            else:
                page = None

            attempts = 0

        except (RussianRadarlyException, RussianRadarlyTimeout):
            logger.error(f"Russian Radarly call failed for the user {username}")
            attempts += 1

            if attempts > max_attempts:
                logger.error(f"Max attempt reached for the user {username}")
                break

        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error(repr(e))
            break

    logger.info(f"The user {username} has published {len(light_posts)} posts")

    return light_posts
