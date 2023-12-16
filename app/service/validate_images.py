from multiprocessing.dummy import Pool

import requests
import urllib3
from app import logger
from app.helpers.utils import guess_image_mime_type
from selenium_driver.helpers.s3 import get_is_blacklisted_image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def filter_valid_pictures_module(pictures):
    with Pool(5) as p:
        valid_pictures = p.map(__is_picture_valid, pictures)

    valid_pictures = [pic for pic in valid_pictures if pic]

    return valid_pictures


def __is_picture_valid(picture):
    """Return picture itself if picture valid else none"""

    try:
        r = requests.get(
            picture,
            timeout=15,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0",
            },
            verify=False,
        )

    except (requests.exceptions.ReadTimeout, requests.models.ConnectionError):
        logger.info("Timeout on __is_picture_valid")
        return None

    except Exception as ex:
        logger.info(f"Error on __is_picture_valid {ex}")
        return None

    # Check if the content of the image corresponds to the right MIME type
    if r.status_code >= 400 or not guess_image_mime_type(r.content):
        return None

    # Image should be skipped
    if get_is_blacklisted_image(r.content):
        logger.info(f"Skipping Image {picture} as its blacklisted")
        return None

    return picture
