import os
from datetime import datetime
from operator import countOf
from traceback import format_exc
from uuid import uuid4

import jinja2
from tqdm import tqdm

from app import logger, sentry_sdk
from app.dao import PostDAO
from app.helpers.utils import chunks
from app.service.screenshot.instagram.utils import format_caption, format_date, get_as_base64, time_ago
from russian_radarly.lambda_interface import (
    QueryType,
    RussianRadarlyException,
    RussianRadarlyTimeout,
    call_russian_radarly,
)
from selenium_driver.archiving import build_instagram_webshot, init_screenshot_driver

post_dao = PostDAO()


def build_instagram_post_webshot(html_file_path, ig_shortcode, driver=None):
    """Open the HTML file provided, take a screenshot of it and return the S3 storage URL of the image"""

    ig_window_width = 1024
    ig_window_height = 700

    display_url = f"https://www.instagram.com/p/{ig_shortcode}/"

    s3_link = build_instagram_webshot(ig_window_width, ig_window_height, display_url, html_file_path, driver)

    return s3_link


def build_post_screenshot(shortcode):
    # Call the Russian Radarly Lambda
    try:
        post = call_russian_radarly(QueryType.GET_POST_DETAILS, shortcode=shortcode, extended_output=True)
    except (RussianRadarlyException, RussianRadarlyTimeout):
        return None

    s3_link = take_instagram_post_screenshot(post)

    return s3_link


def take_instagram_post_screenshot(post, shared_list=None, driver=None):
    """Build a screenshot for an Instagram post

    Parameters:
    ===========
    post: dict
    shared_list: list which can be shared among multiple processes

    Returns:
    ========
    s3_link: str
        S3 URL where the screenshot is stored
    """

    # We do not handle the screenshot of video posts
    if not post["pictures"]:
        raise AttributeError("Posts containing no pictures are not handled by this Instagram screenshot service")

    nb_pictures = len(post["pictures"])
    first_pic_url = post["pictures"][0]
    publication_datetime = datetime.strptime(post["publication_datetime"], "%Y-%m-%d %H:%M:%S")
    caption = post["caption"]
    nb_likes = post["likes_count"]

    username = post["owner"]["username"]
    profile_pic_url = post["owner"]["profile_pic_url"]
    is_verified = post["owner"]["is_verified"]

    comments = post.get("first_comments", [])
    for comment in comments:
        comment["formatted_text"] = format_caption(comment["text"])
        comment["time_ago"] = time_ago(datetime.strptime(comment["creation_datetime"], "%Y-%m-%d %H:%M:%S"))
        comment["likes_sentence"] = f"{comment['likes_count']:,} like{'s' if comment['likes_count'] > 1 else ''}"
        comment["owner"]["profile_pic"] = get_as_base64(comment["owner"]["profile_pic_url"])

    # Get the appropriate template
    if nb_pictures == 1:
        template_name = "single-image.html"
    else:
        template_name = "multiple-images.html"

    template_path = f"instagram_screenshots/templates/{template_name}"

    try:
        # Build a temporary HTML file (with random name) from the template using Jinja
        file_path = f"instagram_screenshots/tmp/{uuid4()}.html"

        # Make sure that the /tmp folder exists
        os.makedirs("instagram_screenshots/tmp/", exist_ok=True)

        with open(template_path, "r") as f:
            template = f.read()

        like_sentence = ""
        last_liked_by_username = None
        last_liked_by_profile_pic = None

        if nb_likes > -1:
            like_sentence = f"{nb_likes:,} like{'s' if nb_likes > 1 else ''}"
        else:
            last_liked_by = post["last_liked_by"]
            if last_liked_by:
                last_liked_by_username = last_liked_by["username"]
                last_liked_by_profile_pic = get_as_base64(last_liked_by["profile_pic_url"])

        filled_template = jinja2.Template(template).render(
            comments=comments,
            user_name=username,
            is_verified=is_verified,
            picture=get_as_base64(first_pic_url),
            date=format_date(publication_datetime),
            formatted_caption=format_caption(caption),
            caption_time_ago=time_ago(publication_datetime),
            user_profile_picture=get_as_base64(profile_pic_url),
            likes_sentence=like_sentence,
            nb_likes=nb_likes,
            last_liked_by_username=last_liked_by_username,
            last_liked_by_profile_pic=last_liked_by_profile_pic,
        )

        with open(file_path, "w") as f:
            f.write(filled_template)

        # Open a Selenium browser, load the file, resize the window and screenshot
        s3_link = build_instagram_post_webshot(file_path, post["shortcode"], driver=driver)

    finally:
        # Delete the temporary file if it exists
        try:
            os.remove(file_path)
        except Exception:
            raise

    if shared_list is not None:
        shared_list.append(
            {
                "shortcode": post["shortcode"],
                "archive_link": s3_link,
            }
        )

    return s3_link


def build_screenshots_from_posts_batch(posts):
    """
    Parameters:
    ===========
    posts: dict[]
        list of the post details useful for building screenshots

    Returns:
    ========
    archive_links_dict: dict
        {shortcode: archive_link}
    """

    archive_links_dict = dict()

    driver = init_screenshot_driver(domain_name="instagram.com")

    for post in posts:
        try:
            archive_link = take_instagram_post_screenshot(post, driver=driver)
        except Exception:
            logger.error(f"fail to take_instagram_post_screenshot for {post.get('shortcode')}:\n{format_exc()}")
            archive_link = None

        archive_links_dict[post["shortcode"]] = archive_link

    driver.kill_driver()

    return archive_links_dict


def take_instagram_post_screenshots(posts_to_send, scraped_posts, batch_size=16):
    # Build a set of the shortcodes to screenshot (they may be duplicated in posts_to_send)
    shortcodes = list(set([post["shortcode"] for post in posts_to_send]))

    logger.info(f"Building screenshots for {len(shortcodes)} posts...")

    nb_failed_screenshots = 0

    for shortcodes_batch in tqdm(list(chunks(shortcodes, batch_size))):
        # Retrieve the post details associated with the batch of posts to send
        post_details = [scraped_posts[shortcode] for shortcode in shortcodes_batch if shortcode in scraped_posts]

        # Take all the screenshots
        try:
            screenshots_dict = build_screenshots_from_posts_batch(post_details)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            screenshots_dict = {post_dict["shortcode"]: None for post_dict in post_details}
            continue

        # Count the failed screenshots
        nb_failed_screenshots += countOf(screenshots_dict.values(), None)

        for post in [post for post in posts_to_send if post["shortcode"] in shortcodes_batch]:
            post_obj = post["post_object"]
            shortcode = post["shortcode"]

            # Save the screenshot to database
            updated_post = post_dao.set_post_archive_link(post_obj, screenshots_dict[shortcode])

            # Refresh the post object in the list of posts to send
            post["post_object"] = updated_post

    logger.info(f"Successfully built screenshots for {len(shortcodes) - nb_failed_screenshots}/{len(shortcodes)} posts")


if __name__ == "__main__":
    shortcode = "CRWkR9nMXln"  # Chanel counterfeit, no comment
    shortcode = "Bfjfo-pB-rZ"  # Saab post, a few comments
    shortcode = "CVYaKURvxf_"  # post from The Rock with 2 picture, multiple comments
    shortcode = "Cr-PGRmNyJE"  # video post

    print(build_post_screenshot(shortcode))
