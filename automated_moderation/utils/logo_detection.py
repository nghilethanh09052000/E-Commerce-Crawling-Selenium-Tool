from typing import List
from multiprocessing.pool import ThreadPool
import json
import time
from functools import partial

import boto3
from rich.progress import track

from automated_moderation.utils.logger import log
from app.settings import AWS_RISE_ACCESS_KEY_ID, AWS_RISE_SECRET_ACCESS_KEY, AWS_REGION, ML_CACHING_API_KEY


lambda_client = boto3.client(
    "lambda",
    aws_access_key_id=AWS_RISE_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_RISE_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


def get_brands_from_image_url(image_urls: List[str], organisation_name: str) -> dict:
    """Call the logo detection service to determine which brands the images are associated with

    Args:
        image_urls (str[]): list of URLs

    Returns:
        mapping between each image and the brands the image is associated with - e.g. {"url_1": ["brand_1"]}
    """

    log.info(f"Calling logo detection API for {len(image_urls)} images")

    # Create batches of 4 images to avoid logo detection lambda to timeout
    with ThreadPool(100) as p:
        r = list(
            track(
                p.imap(
                    partial(invoke_lambda_logo_detection, organisation_name=organisation_name), image_urls, chunksize=8
                ),
                total=len(image_urls),
            )
        )

    # Concatenate the results into a single dict
    results = {image_url: brands for batch in r for image_url, brands in batch.items()}
    return results


def invoke_lambda_logo_detection(image_url, organisation_name: str):
    request_payload = {
        "headers": {"x-api-key": ML_CACHING_API_KEY},
        "image_url": image_url,
        "get_logo_detection": True,
        "organisation_name": organisation_name,
    }

    # Try 3 times to avoid being trapped by cold start of Lambda, which can generate timeouts
    response = {}
    for _ in range(3):

        try:
            response = json.loads(
                lambda_client.invoke(
                    FunctionName="ml-caching-lambda",
                    Payload=json.dumps(request_payload),
                )["Payload"].read()
            )

            if not response.get("errorMessage"):
                # Success
                return {image_url: response.get("logo_detection_result")}

        except Exception as e:
            time.sleep(5)
            print(repr(e))
            continue

    return {}
