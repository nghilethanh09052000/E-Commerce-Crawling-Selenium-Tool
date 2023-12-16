from typing import List, Dict
from itertools import repeat
from multiprocessing.pool import ThreadPool

from automated_moderation.dataset import BasePost
from app import logger, sentry_sdk
from app.dao import OrganisationDAO
from app.api.logo_detection import lambda_client, get_brands_from_image_url
from app.helpers.translation import translate_post_text
from app.settings import PREFILTERING_API_KEY
from app.helpers.utils import chunks
from navee_utils.aws_lambda import invoke_lambda

MARKETPLACE_FILTERING_ORG = []
FILTERING_RATE = 0.01

organisation_DAO = OrganisationDAO()


def prefiltering_predictions(posts: List[BasePost], model_name: str) -> Dict:
    batch_size = 100

    logger.info(f"Calling prefiltering API for {len(posts)} posts by batch of {batch_size} posts")
    posts_batch = list(chunks(posts, batch_size))

    with ThreadPool(4) as p:
        r = list(p.starmap(invoke_prediction_lambda, zip(posts_batch, repeat(model_name)), chunksize=8))

    logger.info("Prefiltering API call completed")

    return {post_id: post for batch in r for post_id, post in batch.items()}


def invoke_prediction_lambda(posts: List[BasePost], model_name: str) -> Dict:
    request_payload = {
        "headers": {"x-api-key": PREFILTERING_API_KEY},
        "posts": [post.to_json() for post in posts],
        "model_name": model_name,
    }

    return (
        invoke_lambda(
            function_name="prefiltering-lambda",
            request_payload=request_payload,
            sentry_sdk=sentry_sdk,
            lambda_client=lambda_client,
        )
        or {}
    )


def filter_by_exclude_keywords(posts: List[dict], exclude_keywords: List[str]) -> List[dict]:
    logger.info(f"Filtering by exclude keywords, current count {len(posts)}")

    posts_to_scrape = []
    for post in posts:
        title = post.get("title") or ""
        description = post.get("description") or ""

        if not any(keyword.lower() in f"{title.lower()} {description.lower()}" for keyword in exclude_keywords):
            posts_to_scrape.append(post)

    logger.info(f"Filtering by exclude keywords complete, current count {len(posts_to_scrape)}")

    return posts_to_scrape


def filter_by_must_have_keywords(posts: List[dict], must_have_keywords: List[str]) -> List[dict]:
    logger.info(f"Filtering by must have keywords, current count {len(posts)}")

    posts_to_scrape = []
    for post in posts:
        title = post.get("title") or ""
        description = post.get("description") or ""

        translated_title, translated_desc, _ = translate_post_text(title, description)
        translated_title = translated_title or ""
        translated_desc = translated_desc or ""

        if any(
            keyword.lower()
            in f"{title.lower()} {description.lower()} {translated_title.lower()} {translated_desc.lower()}"
            for keyword in must_have_keywords
        ):
            posts_to_scrape.append(post)

    logger.info(f"Filtering by must have keywords complete, current count {len(posts_to_scrape)}")

    return posts_to_scrape


def dispatch_among_organisations(posts: list) -> list:
    logger.info(f"Dispatching posts among the organisations, current count {len(posts)}")

    keywords_list = organisation_DAO.get_organisation_keywords()

    for post in posts:
        post_organisations = get_post_organisation(post, keywords_list)

        if len(post_organisations) > 0:
            post["organisation_names"] = post_organisations
        else:
            # try with logo detection case yupoo szwego
            if post.get("pictures"):
                image_urls = [
                    image["s3_url"] if image.get("s3_url") else image["picture_url"] for image in post.get("pictures")
                ]
                logger.info(f"Passing {image_urls} for brand logo detection")
                logo_predictions = get_brands_from_image_url(image_urls)
                if logo_predictions:
                    organisation_list = list(
                        {
                            organisation
                            for image_organisations in logo_predictions.values()
                            for organisation in image_organisations
                        }
                    )
                    logger.info(f"Post {post['url']} detected logo for {organisation_list}")
                    post["organisation_names"] = organisation_list
                    continue
            posts.remove(post)

    logger.info(f"Dispatching complete, new count {len(posts)}")

    return posts


def get_post_organisation(post: Dict, keywords_list) -> List[str]:
    """checks if keyword in post title or description { keyword : organisation_name , keyword2: organisation_name_2}"""

    title = post.get("title", "").lower() if post.get("title", "") else ""
    description = post.get("description", "").lower() if post.get("description", "") else ""

    logger.info(f"Checking if data exists in title: {title} - description:{description}")

    organisations = []
    for keyword in keywords_list:
        if keyword in title or keyword in description:
            logger.info(f"Found keyword {keyword} in organisation {keywords_list[keyword]}")
            organisations.append(keywords_list[keyword])

    # Remove duplicates
    organisations = list(set(organisations))
    return organisations
