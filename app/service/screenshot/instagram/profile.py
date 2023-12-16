import os
from operator import countOf
from traceback import format_exc
from uuid import uuid4

import jinja2
from tqdm import tqdm

from app import logger, sentry_sdk
from app.helpers.utils import chunks
from russian_radarly.lambda_interface import (
    QueryType,
    RussianRadarlyException,
    RussianRadarlyTimeout,
    call_russian_radarly,
)
from selenium_driver.archiving import build_instagram_webshot, init_screenshot_driver

from app.service.screenshot.instagram.utils import big_count, get_as_base64, get_post_icon_div

from app.dao import PosterDAO


poster_dao = PosterDAO()


def build_instagram_profile_webshot(html_file_path, ig_username, driver=None):
    """Open the HTML file provided, take a screenshot of it and return the S3 storage URL of the image"""

    ig_window_width = 1024
    ig_window_height = 1200

    display_url = f"https://www.instagram.com/{ig_username}/"

    s3_link = build_instagram_webshot(ig_window_width, ig_window_height, display_url, html_file_path, driver)

    return s3_link


def build_profile_screenshot(username):
    # Call the Russian Radarly Lambda
    try:
        profile = call_russian_radarly(QueryType.GET_PROFILE_DETAILS, username=username)
    except (RussianRadarlyException, RussianRadarlyTimeout):
        return None

    return take_instagram_profile_screenshot(profile)


def take_instagram_profile_screenshot(profile, shared_list=None, driver=None):
    """Build a screenshot for an Instagram account

    Parameters:
    ===========
    profile: dict
    shared_list: list which can be shared among multiple processes

    Returns:
    ========
    s3_link: str
        S3 URL where the screenshot is stored
    """

    user = profile["user"]
    username = user["username"]
    profile_pic_url = user["profile_pic_url"]
    is_verified = user["is_verified"]
    posts_count = user["posts_count"]
    followers_count = user["followers_count"]
    followings_count = user["followings_count"]
    full_name = user["full_name"]
    biography = user["biography"].replace("\n", "<br>")
    external_url = user["external_url"]
    has_story = user["has_story"]

    reels_count = user["reels_count"]
    videos_count = user["videos_count"]

    posts = profile["media"]["posts"]  # keys pictures, is_video, is_clip -> determines which SVG icon to display

    posts_count_sentence = big_count(posts_count)
    followers_count_sentence = big_count(followers_count)
    followings_count_sentence = big_count(followings_count)

    for post in posts:
        post["first_picture_base64"] = get_as_base64(post["pictures"][0])
        post["icon_div"] = get_post_icon_div(post)

    # Group the posts 3 by 3 (3 posts correspond to one line of posts in the screenshot)
    three_posts_batches = [posts[n : n + 3] for n in range(0, len(posts), 3)]

    profile_template_path = "instagram_screenshots/templates/profile.html"

    try:
        # Build a temporary HTML file (with random name) from the template using Jinja
        file_path = f"instagram_screenshots/tmp/{uuid4()}.html"

        # Make sure that the /tmp folder exists
        os.makedirs("instagram_screenshots/tmp/", exist_ok=True)

        with open(profile_template_path, "r") as f:
            template = f.read()

        profile_pic_base64 = get_as_base64(profile_pic_url)

        filled_template = jinja2.Template(template).render(
            username=username,
            profile_pic_base64=profile_pic_base64,
            is_verified=is_verified,
            posts_count=posts_count,
            posts_count_sentence=posts_count_sentence,
            followers_count=followers_count,
            followers_count_sentence=followers_count_sentence,
            followings_count=followings_count,
            followings_count_sentence=followings_count_sentence,
            full_name=full_name,
            biography=biography,
            external_url=external_url,
            has_story=has_story,
            reels_count=reels_count,
            videos_count=videos_count,
            three_posts_batches=three_posts_batches,
        )

        with open(file_path, "w") as f:
            f.write(filled_template)

        # Open a Selenium browser, load the file, resize the window and screenshot
        s3_link = build_instagram_profile_webshot(file_path, username, driver=driver)

    finally:
        # Delete the temporary file if it exists
        try:
            os.remove(file_path)
        except Exception:
            raise

    if shared_list is not None:
        shared_list.append(
            {
                "username": username,
                "archive_link": s3_link,
            }
        )

    return s3_link


def build_screenshots_from_instagram_profiles(profiles):
    """
    Parameters:
    ===========
    profiles: dict[]
        list of the profile details useful for building screenshots

    Returns:
    ========
    archive_links_dict: dict
        {username: archive_link}
    """

    archive_links_dict = dict()

    driver = init_screenshot_driver(domain_name="instagram.com")

    for profile in profiles:
        try:
            archive_link = take_instagram_profile_screenshot(profile, driver=driver)
        except Exception:
            logger.error(f"fail to take_instagram_profile_screenshot for {profile.get('username')}:\n{format_exc()}")
            archive_link = None

        archive_links_dict[profile["username"]] = archive_link

    driver.kill_driver()

    return archive_links_dict


def take_instagram_profile_screenshots(profiles_to_send, scraped_posters, batch_size=16):
    # Build a set of the usernames to screenshot (there may be duplicated in profiles_to_send)
    usernames = list(set([profile["username"] for profile in profiles_to_send]))

    logger.info(f"Building screenshots for {len(usernames)} profiles...")

    nb_failed_screenshots = 0

    for usernames_batch in tqdm(list(chunks(usernames, batch_size))):
        # Retrieve the profile details associated with the batch of profiles to send
        profile_details = [scraped_posters[username] for username in usernames_batch]

        # Take all the screenshots
        try:
            screenshots_dict = build_screenshots_from_instagram_profiles(profile_details)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            screenshots_dict = {profile_dict["username"]: None for profile_dict in profile_details}
            continue

        # Count the failed screenshots
        nb_failed_screenshots += countOf(screenshots_dict.values(), None)

        for profile in [profile for profile in profiles_to_send if profile["username"] in usernames_batch]:
            profile_obj = profile["profile_object"]
            username = profile["username"]

            # Save the screenshot to database
            updated_profile = poster_dao.set_profile_archive_link(profile_obj, screenshots_dict[username])

            # Refresh the profile object in the profiles_to_send list
            profile["profile_object"] = updated_profile

    logger.info(
        f"Successfully built screenshots for {len(usernames) - nb_failed_screenshots}/{len(usernames)} profiles"
    )


if __name__ == "__main__":
    usernames = [
        "gucci",
    ]

    for username in usernames:
        print(f"{username}: {build_profile_screenshot(username)}")
