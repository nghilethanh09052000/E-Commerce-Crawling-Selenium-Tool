import os
from typing import Optional
import imagehash
from io import BytesIO
from PIL import Image
import boto3
from botocore.exceptions import NoCredentialsError

from selenium_driver import logger
from selenium_driver.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    SPECIFIC_SCRAPER_AWS_BUCKET,
)
from selenium_driver.helpers.blacklisted_images import BLACKLISTED_IMAGES

from navee_utils.image import upload_image
from navee_utils.requests import requests_retry_session


BASE_PATH_S3 = f"https://s3-eu-west-1.amazonaws.com/{SPECIFIC_SCRAPER_AWS_BUCKET}/"

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def get_is_blacklisted_image(image):
    """Check the image hash against a known set of blacklisted image hashes or size is not valid"""

    # to small to be a valid image
    if len(image) < 100:
        return None, False

    # Generate Image Hash
    image_hash = imagehash.phash(Image.open(BytesIO(image)), hash_size=10)

    for blacklisted_image_hex in BLACKLISTED_IMAGES.values():
        blacklisted_image_hash = imagehash.hex_to_hash(blacklisted_image_hex)
        # Check if the images are similar
        if blacklisted_image_hash == image_hash:
            # these images are similar and it is a blacklisted image
            return True
        else:
            return False


def upload_image_from_url(url: str, path: str = "images") -> Optional[str]:

    is_blacklisted_image = False

    try:
        img = (
            requests_retry_session(retries=2, backoff_factor=2)
            .get(
                url,
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
            .content
        )

        is_blacklisted_image = get_is_blacklisted_image(img)
        # Image Hash Blacklisted
        if is_blacklisted_image:
            logger.info(f"Image {url} is blacklisted and should be skipped")
            return None, True

        uploaded_image = upload_image(
            s3_client=s3,
            bucket=SPECIFIC_SCRAPER_AWS_BUCKET,
            path=path,
            img=img,
        )

    except Exception as e:
        logger.info(f"image was not uploaded: {repr(e)}")
        return None, is_blacklisted_image

    return uploaded_image, is_blacklisted_image


def upload_image_from_bytes(img: bytes, path: str = "images") -> Optional[str]:
    is_blacklisted_image = get_is_blacklisted_image(img)

    # Image Hash Blacklisted
    if is_blacklisted_image:
        logger.info("Image is blacklisted and should be skipped")
        return None, is_blacklisted_image

    return (
        upload_image(
            s3_client=s3,
            bucket=SPECIFIC_SCRAPER_AWS_BUCKET,
            path=path,
            img=img,
        ),
        is_blacklisted_image,
    )


def upload_file_to_s3(local_file, bucket, file_name, make_public=False, file_type=None):
    ExtraArgs = {}
    if make_public:
        ExtraArgs["ACL"] = "public-read"

    if file_type:
        ExtraArgs["ContentType"] = file_type

    try:
        s3.upload_file(local_file, bucket, file_name, ExtraArgs=ExtraArgs)

        # If the upload is successful, return a success message and the file link
        s3_link = "https://s3-eu-west-1.amazonaws.com/" + bucket + "/" + file_name

        return "Upload successful", s3_link

    except FileNotFoundError:
        return "The file was not found", False
    except NoCredentialsError:
        return "Credentials not available", False


def download_folder_from_s3(bucket_name, object_key, file_path):
    try:
        print(f"Trying to Download {object_key}")
        objects = s3.list_objects(Bucket=bucket_name, Prefix=object_key)["Contents"]
        for obj in objects:
            key = obj["Key"]
            if key.endswith("/"):
                ## create needed folder
                if not os.path.exists(file_path + key):
                    print("creating missing directory")
                    os.makedirs(file_path + key)
            else:
                if not os.path.exists(file_path + key[0 : key.rindex("/")]):
                    print("creating missing directory")
                    os.makedirs(file_path + key[0 : key.rindex("/")])
                s3.download_file(bucket_name, key, file_path + key)
    except FileNotFoundError:
        return "The file was not found"
    except NoCredentialsError:
        return "Credentials not available"
