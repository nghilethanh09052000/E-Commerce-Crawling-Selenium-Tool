import os
from uuid import uuid4

from selenium_driver.helpers.s3 import upload_file_to_s3
from selenium_driver import logger
from selenium_driver.settings import sentry_sdk
from selenium_driver.settings import SPECIFIC_SCRAPER_AWS_BUCKET, ENVIRONMENT_NAME


def save_html(str, file_name=uuid4()):
    file_path = "{}_page_source.html".format(file_name)

    try:
        with open(file_path, "w") as f:
            f.write(str)

        _, s3_link = upload_file_to_s3(
            local_file=file_path,
            bucket=SPECIFIC_SCRAPER_AWS_BUCKET,
            file_name="{}/page_soucre/{}.html".format(ENVIRONMENT_NAME, file_name),
        )
        # reomve file
        os.remove(file_path)

    except Exception as ex:
        logger.info(f"Error on save_html {repr(ex)}")
        sentry_sdk.capture_exception(ex)
        s3_link = None

    return s3_link
