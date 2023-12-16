from multiprocessing.pool import ThreadPool
from typing import List

import boto3
from tqdm import tqdm

from navee_utils.aws_lambda import invoke_lambda
from app import logger
from app.settings import (
    AWS_RISE_ACCESS_KEY_ID,
    AWS_RISE_SECRET_ACCESS_KEY,
    AWS_REGION,
    ML_CACHING_API_KEY,
    sentry_sdk,
)
from automated_moderation.dataset import BasePost

lambda_client = boto3.client(
    "lambda",
    aws_access_key_id=AWS_RISE_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_RISE_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


def get_logo_prediction(light_posts: List[BasePost]):
    """Returns a mapping between each image and the brands the image is associated with - e.g. {"url_1": ["brand_1"]}"""

    picture_urls = []
    for post in light_posts:
        picture_urls += [image.s3_url or image.url for image in post.images]

    return get_brands_from_image_url(picture_urls)


def get_brands_from_image_url(image_urls: List[str]) -> dict:
    """Call the logo detection service to determine which brands the images are associated with

    Args:
        image_urls (str[]): list of URLs

    Returns:
        mapping between each image and the brands the image is associated with - e.g. {"url_1": ["brand_1"]}
    """

    logger.info(f"Calling logo detection API for {len(image_urls)} images")

    # Create batches of 4 images to avoid logo detection lambda to timeout
    with ThreadPool(10) as p:
        r = list(tqdm(p.imap(invoke_lambda_logo_detection, image_urls, chunksize=8), total=len(image_urls)))

    # Concatenate the results into a single dict
    results = {image_url: brands for batch in r for image_url, brands in batch.items()}
    return results


def invoke_lambda_logo_detection(image_url):

    request_payload = {
        "headers": {"x-api-key": ML_CACHING_API_KEY},
        "image_url": image_url,
        "get_logo_detection": True,
    }

    lambda_response = invoke_lambda(
        function_name="ml-caching-lambda",
        request_payload=request_payload,
        sentry_sdk=sentry_sdk,
        lambda_client=lambda_client,
        required_fields=["logo_detection_result"],
    )

    if not lambda_response:
        return {}

    return {image_url: lambda_response["logo_detection_result"]}


if __name__ == "__main__":
    image_urls = [
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/073a7334-200f-4c4d-b52e-648306f81610.jpeg"
    ]
    res = get_brands_from_image_url(image_urls)
    print(res)
