from typing import Optional, Tuple
from io import BytesIO
import hashlib
import logging
import requests
import numpy as np
import math

from PIL import Image
import pillow_avif  # noqa - do not remove: require to open avif images
from botocore.exceptions import ClientError

from .errors import BadImage

IMAGE_HASH_SALT = "SuolVDrtu8zKDihyNgB9COWyEU8DThADDggjcGDgh0zQ17JFMlqY9mUwXnUfmccD"
BASE_PATH_S3 = "https://s3-eu-west-1.amazonaws.com"


def upload_image(s3_client, bucket: str, path: str, img: bytes) -> Optional[str]:
    # check the image format, if avif, we convert it
    # attention! We need this until we deploy new url_to_img everywhere
    img, img_type = convert_avif_images(img)

    # get type from mymetype
    if img_type is None and not (img_type := guess_image_mime_type(img)):
        logging.error("cannot determine image type")
        return

    # resize the large file
    img = resize_image(img)

    # Get image hash using sha256
    img_with_salt = img + bytes(IMAGE_HASH_SALT, encoding="utf8")
    img_name = (
        hashlib.sha256(img_with_salt).hexdigest() + f'.{img_type.replace("image/", "")}'
    )
    img_path = path.strip("/") + "/" + img_name

    try:
        s3_client.upload_fileobj(
            BytesIO(img),
            bucket,
            img_path,
            ExtraArgs={"ACL": "public-read", "ContentType": img_type},
        )
    except ClientError as e:
        logging.error(e, exc_info=True)
        return

    return BASE_PATH_S3 + "/" + bucket + "/" + img_path


def convert_avif_images(img: bytes) -> Tuple[bytes, str]:
    img_type = None

    try:
        opened_img = Image.open(BytesIO(img))
    except OSError as e:
        logging.error(e, exc_info=True)
    else:
        if opened_img.format.lower() == "avif":
            buf = BytesIO()
            opened_img.save(buf, format="PNG")
            img = buf.getvalue()
            img_type = "image/png"

    return img, img_type


def guess_image_mime_type(
    img_bytes: bytes, truncated_allowed: bool = False
) -> Optional[str]:
    try:
        img = Image.open(BytesIO(img_bytes))
        if not truncated_allowed:
            img.load()  # OSError if truncated
        mime_type = img.get_format_mimetype()
    except OSError:
        return

    if mime_type.startswith("image"):
        return mime_type


def url_to_bytes(url: str) -> bytes:
    # User-Agent is better to keep with latest version of Firefox.
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0",
            },
            verify=False,
        )
        img_bytes = r.content
        status_code = r.status_code
    except requests.exceptions.Timeout:
        raise BadImage(f"Unable to fetch image '{url}': request timeout")
    except requests.exceptions.ConnectionError:
        # this one is too ugly to show to users
        raise BadImage(f"Unable to fetch image '{url}': Conection error")
    except Exception as e:
        raise BadImage(f"Unable to fetch image '{url}': {e}")

    if status_code >= 400:
        raise BadImage(
            f"Unable to fetch image '{url}': bad http code '{r.status_code}'"
        )

    if img_bytes:
        return img_bytes
    else:
        return


def bytes_to_img(img_bytes: bytes) -> np.ndarray:
    img = Image.open(BytesIO(img_bytes))

    # test if img is animation
    if hasattr(img, "n_frames"):
        if img.n_frames > 1:
            img.seek(img.n_frames // 2)

    frame_to_detect = img.copy().convert("RGB")
    return np.array(frame_to_detect)


def url_to_img(url: str) -> np.ndarray:
    return bytes_to_img(url_to_bytes(url))


def resize_image(img_bytes: bytes) -> bytes:
    file_size = len(img_bytes) // 1024 // 1024

    if file_size > 10:
        scale = int(math.sqrt(file_size // 10)) + 1
        img = Image.open(BytesIO(img_bytes))
        w, h = img.size
        new_img = img.resize((w // scale, h // scale))

        bytes_io = BytesIO()
        new_img.save(bytes_io, format=img.format)
        new_img_bytes = bytes_io.getvalue()

        return new_img_bytes
    else:
        return img_bytes
