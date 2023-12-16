import requests
from enum import Enum
import time
from typing import List, Optional

from rich.progress import track

from automated_moderation.dataset import BasePost, BaseImage, BasePoster, BaseOrganisation
from selenium_driver.helpers.s3 import upload_image_from_url
from app import logger, sentry_sdk

ACCESS_TOKEN = "ZXlKMGVYQWlPaUpLVjFRaUxDSmhiR2NpT2lKSVV6STFOaUo5LmV5SnpkV0lpT2lKT1lYWmxaU0lzSW1saGRDSTZNVFk0TmpVMk5EVTFNaTR5TWpnMU9UWTNmUS43R3ZWM1ZibEQ4Z2ZoQVByTGdxd3Q5WHY0akxQU2FGb2N2YW5JYTF5WjZR"
API_BASE_URL = "https://api.data365.co/v1.1"


class TaskStatus(Enum):
    FINISHED = "finished"
    CREATED = "created"
    NOT_CREATED = "unknown"
    PENDING = "pending"
    FAIL = "fail"


def create_search_task(search_query: str, max_posts: int = 3000, auto_update_interval: int = 43200):
    res = requests.post(
        f"{API_BASE_URL}/facebook/search/{search_query}/posts/latest/update?access_token={ACCESS_TOKEN}&max_posts={max_posts}&auto_update_interval={auto_update_interval}"
    )

    if not res.ok or res.json()["status"] != "accepted":
        raise RuntimeError(f"Error creating task: {res.text}")


def get_search_task_status(search_query: str, max_posts: int = 3000, auto_update_interval: int = 43200) -> TaskStatus:
    res = requests.get(
        f"{API_BASE_URL}/facebook/search/{search_query}/posts/latest/update?access_token={ACCESS_TOKEN}&max_posts={max_posts}&auto_update_interval={auto_update_interval}"
    )
    return TaskStatus(res.json()["data"]["status"])


def get_profile_task_status(profile_id: str) -> TaskStatus:
    res = requests.get(
        f"{API_BASE_URL}/facebook/profile/{profile_id}/update?access_token={ACCESS_TOKEN}&load_feed_posts=false"
    )
    return TaskStatus(res.json()["data"]["status"])


def get_post_task_status(post_id: str) -> TaskStatus:
    res = requests.get(f"{API_BASE_URL}/facebook/post/{post_id}/update?access_token={ACCESS_TOKEN}")
    return TaskStatus(res.json()["data"]["status"])


def create_profile_task(profile_id: str):
    res = requests.post(
        f"{API_BASE_URL}/facebook/profile/{profile_id}/update?access_token={ACCESS_TOKEN}&load_feed_posts=false&page_screenshot=true"
    )

    if not res.ok or res.json()["status"] != "accepted":
        raise RuntimeError(f"Error creating task: {res.text}")


def create_post_task(post_id: str, get_screenshot: bool = True):
    res = requests.post(
        f"{API_BASE_URL}/facebook/post/{post_id}/update?access_token={ACCESS_TOKEN}&upload_posts_screenshots_to_s3={get_screenshot}"
    )

    if not res.ok or res.json()["status"] != "accepted":
        raise RuntimeError(f"Error creating task: {res.text}")


def list_tasks():
    res = requests.get(f"{API_BASE_URL}/facebook/search/posts/tasks?access_token={ACCESS_TOKEN}&max_page_size=50")
    print(res.json()["data"]["items"])


def get_all_posts(search_query: str, max_posts_to_browse: Optional[int]) -> List[dict]:
    valid_posts = []
    try:
        url = f"{API_BASE_URL}/facebook/search/{search_query}/posts/latest/posts?access_token={ACCESS_TOKEN}"

        res = requests.get(url)
        valid_posts += [p for p in res.json()["data"]["items"] if p["attached_medias_id"]]

        logger.info(f"Found {len(valid_posts)} valid posts")

        if max_posts_to_browse is not None and len(valid_posts) >= max_posts_to_browse:
            return valid_posts

        while res.json()["data"]["page_info"]["has_next_page"]:
            cursor = res.json()["data"]["page_info"]["cursor"]
            res = requests.get(url + f"&cursor={cursor}")
            valid_posts += [p for p in res.json()["data"]["items"] if p["attached_medias_id"]]

            logger.info(f"Found {len(valid_posts)} valid posts")

            if max_posts_to_browse is not None and len(valid_posts) >= max_posts_to_browse:
                valid_posts = valid_posts[:max_posts_to_browse]
                return valid_posts

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("URL", url)
            scope.set_extra("Reponse", res.text)
            scope.set_extra("Search query", search_query)
            sentry_sdk.capture_exception(e)

        logger.error(f"Error getting posts: {repr(e)}")

    return valid_posts


def get_all_posts_formatted(
    organisation_name: str, search_query: str, max_posts_to_browse: Optional[int]
) -> List[BasePost]:
    posts = get_all_posts(search_query, max_posts_to_browse)

    formatted_posts = []
    for post in track(posts, description="Formatting posts", total=len(posts)):
        formatted_posts.append(
            BasePost(
                images=[
                    BaseImage(
                        url=media,
                    )
                    for media in post["attached_medias_preview_url"]
                ],
                created_at=post["created_time"],
                id=post["id"],
                url=f"https://www.facebook.com/{post['id']}",
                poster=BasePoster(
                    name=post["owner_full_name"],
                    id=post["owner_id"],
                    url=f"https://www.facebook.com/{post['owner_id']}",
                    website_identifier=post["owner_id"],
                ),
                description=post["text"],
                organisation=BaseOrganisation(name=organisation_name),
            )
        )

    return formatted_posts


def data365_post_search(
    organisation_name: str, search_queries: List[str], max_posts_to_browse: Optional[int] = None
) -> List[BasePost]:
    posts = []
    search_queries = [s.replace(" ", "%20") for s in search_queries]

    # Create the tasks
    for search_query in track(search_queries):
        if get_search_task_status(search_query) == TaskStatus.NOT_CREATED:
            logger.info(f"Creating task for search query: {search_query}")
            create_search_task(search_query)

    # Get the posts
    for search_query in search_queries:
        logger.info(f"Getting posts for search query: {search_query}")

        max_posts_left_to_scrape = max_posts_to_browse - len(posts) if max_posts_to_browse is not None else None
        if max_posts_left_to_scrape is not None and max_posts_left_to_scrape <= 0:
            break

        task_status = get_search_task_status(search_query)

        while task_status != TaskStatus.FINISHED:
            time.sleep(10)
            logger.info("Waiting for task to be ready...")
            task_status = get_search_task_status(search_query)

        posts += get_all_posts_formatted(
            organisation_name,
            search_query,
            max_posts_to_browse=max_posts_left_to_scrape,
        )

    return posts


def get_poster(poster_id: str) -> dict:
    try:
        res = requests.get(f"{API_BASE_URL}/facebook/profile/{poster_id}?access_token={ACCESS_TOKEN}")
        logger.info(f"Poster {poster_id} successfully retrieved")
        return res.json()["data"]

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("Reponse", res.text)
            sentry_sdk.capture_exception(e)

        logger.error(f"Error getting poster {poster_id}: {repr(e)}")


def get_post(post_id: str) -> dict:
    try:
        res = requests.get(f"{API_BASE_URL}/facebook/post/{post_id}?access_token={ACCESS_TOKEN}")
        logger.info(f"Post {post_id} successfully retrieved")
        return res.json()["data"]

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_extra("Reponse", res.text)
            sentry_sdk.capture_exception(e)

        logger.error(f"Error getting post {post_id}: {repr(e)}")


def get_poster_formatted(poster_id: str) -> BasePoster:
    poster = get_poster(poster_id)

    return BasePoster(
        id=poster["id"],
        username=poster["username"],
        name=poster["full_name"],
        description=poster["biography"],
        url=f"https://www.facebook.com/{poster['id']}",
        profile_pic_url=upload_image_from_url(poster["profile_photo_url"])[0],
        archive_link=upload_image_from_url(poster["profile_screenshot_url"])[0],
        followers_count=poster["followers_count"],
    )


def get_post_formatted(post_id: str, organisation_name: str) -> BasePost:
    post = get_post(post_id)
    formatted_post = BasePost(
        images=[
            BaseImage(
                url=media,
                s3_url=upload_image_from_url(media)[0],
            )
            for media in post["attached_medias_preview_url"]
        ],
        created_at=post["created_time"],
        id=post["id"],
        url=f"https://www.facebook.com/{post['id']}",
        poster=BasePoster(
            name=post["owner_full_name"],
            id=post["owner_id"],
            url=f"https://www.facebook.com/{post['owner_id']}",
            website_identifier=post["owner_id"],
        ),
        description=post["text"],
        organisation=BaseOrganisation(name=organisation_name),
        archive_link=upload_image_from_url(post["post_screenshot"])[0],
    )

    return formatted_post


def data365_poster_search(poster_ids: List[str]) -> List[BasePoster]:
    for poster_id in track(poster_ids):
        if get_profile_task_status(poster_id) == TaskStatus.NOT_CREATED:
            try:
                logger.info(f"Creating task for poster id: {poster_id}")
                create_profile_task(poster_id)
            except Exception as e:
                logger.error(f"Error creating task for poster {poster_id}: {repr(e)}")
                poster_ids.remove(poster_id)

    posters = []
    for poster_id in poster_ids:
        try:
            logger.info(f"Getting poster {poster_id}")

            task_status = get_profile_task_status(poster_id)
            while task_status != TaskStatus.FINISHED:
                if task_status == TaskStatus.FAIL:
                    raise RuntimeError(f"Task failed for poster {poster_id}")

                time.sleep(10)
                logger.info(f"Waiting for task to be ready... current status: {task_status}")
                task_status = get_profile_task_status(poster_id)

            posters.append(get_poster_formatted(poster_id))
        except Exception as e:
            logger.error(f"Error getting poster {poster_id}: {repr(e)}")

    return posters


def data365_post_scraping(post_ids: List[str], organisation_name: str) -> List[BasePost]:
    for post_id in track(post_ids):
        try:
            if get_post_task_status(post_id) == TaskStatus.NOT_CREATED:
                logger.info(f"Creating task for post id: {post_id}")
                create_post_task(post_id)
        except Exception as e:
            logger.error(f"Error creating task for post {post_id}: {repr(e)}")
            post_ids.remove(post_id)

    posts = []
    for post_id in track(post_ids, description="Getting posts"):
        try:
            logger.info(f"Getting post {post_id}")

            task_status = get_post_task_status(post_id)
            while task_status != TaskStatus.FINISHED:
                if task_status == TaskStatus.FAIL:
                    raise RuntimeError(f"Task failed for post {post_id}")

                time.sleep(10)
                logger.info(f"Waiting for task to be ready... current status: {task_status}")
                task_status = get_post_task_status(post_id)

            posts.append(get_post_formatted(post_id, organisation_name=organisation_name))
        except Exception as e:
            logger.error(f"Error getting post {post_id}: {repr(e)}")

    return posts


if __name__ == "__main__":
    # search_query = "chanel replica"
    # for post in data365_post_search("Chanel_Navee", [search_query], max_posts_to_browse=10):
    #     print(post)

    print(data365_poster_search(["100094394870296"]))
