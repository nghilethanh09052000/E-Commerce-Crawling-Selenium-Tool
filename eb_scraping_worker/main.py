from flask import Response, request
import json
import traceback

from app import app
from app.dao import RedisDAO
from app.models import engine
from app.models.enums import UrlPageType
from app.service.scrape import scrape
from app.settings import sentry_sdk
from eb_scraping_worker import logger
from eb_scraping_worker.prepare import prepare_scraping_params

redis_DAO = RedisDAO()
engine.dispose()


@app.route("/", methods=["POST"])
def work_on_message():
    logger.input(message="Worker received a message")
    worker_input = request.get_json()
    try:
        success = scraping_worker(worker_input)
    except AssertionError as e:
        logger.error(repr(e))
        sentry_sdk.capture_exception(e)
        status_code = "400"
    else:
        if success:
            status_code = "200"
        else:
            status_code = "500"
    response = Response(status=status_code)
    logger.output(message="Worker finished processing the message", status_code=status_code)
    return response


def scraping_worker(worker_input):
    logger.info(f"scraping_worker's input: {worker_input}")
    page_type = worker_input.get("page_type")
    assert page_type, "worker_input missing mandatory field: 'page_type' (only 'POST' or 'POSTER')"

    scraping_params = prepare_scraping_params(worker_input)
    logger.info(f"scraping_params are: {scraping_params}")

    update_upload_status_if_needed(worker_input)
    try:
        _, scraped_posts, scraped_posters = scrape(**scraping_params)
    except Exception as e:
        logger.error(traceback.format_exc())
        sentry_sdk.capture_exception(e)
        scraped_posts = None
        scraped_posters = None
    update_upload_status_if_needed(worker_input, scraping_result=(scraped_posts, scraped_posters))

    url = worker_input.get("url")
    if scraped_posts and page_type == UrlPageType.POST.name:
        logger.info(f"Completed scraping post from {url} | {scraped_posts}")
        return True
    elif scraped_posters and page_type == UrlPageType.POSTER.name:
        logger.info(f"Completed scraping poster from {url} | {scraped_posters}")
        return True
    else:
        logger.info(f"no result from 'scrape' for {url}")
        return False


def update_upload_status_if_needed(worker_input, scraping_result=None):
    upload_id = worker_input.get("upload_id")
    upload_request_id = worker_input.get("upload_request_id")
    if upload_id is None or upload_request_id is None:
        return

    if not scraping_result:
        redis_DAO.set_url_upload_status(upload_request_id, upload_id, "started")
        return

    scraped_posts, scraped_posters = scraping_result
    page_type = worker_input.get("page_type")
    status = None
    if page_type == UrlPageType.POST.name:
        if not scraped_posts:
            status = "failed"
        elif worker_input.get("domain_name") == "instagram.com":
            pass
        elif scraped_posts[0].get("sent_to_insertion"):
            status = "sent_to_insertion"
        else:
            status = "ended"
    elif page_type == UrlPageType.POSTER.name and not scraped_posters:
        status = "failed"
    if status:
        redis_DAO.set_url_upload_status(upload_request_id, upload_id, status)


def run_worker_from_queue():

    import boto3
    from app.settings import SCRAPING_QUEUE

    sqs = boto3.resource("sqs", region_name="eu-west-1")
    queue = sqs.get_queue_by_name(QueueName=SCRAPING_QUEUE)

    messages = queue.receive_messages(AttributeNames=["All"], MaxNumberOfMessages=10)
    while len(messages) > 0:
        for message in messages:
            worker_input = json.loads(message.body)
            try:
                scraping_worker(worker_input)
            except Exception as e:
                logger.error(f"Worker failed for input: {worker_input}\n{traceback.format_exc()}")
                sentry_sdk.capture_exception(e)
            message.delete()
        messages = queue.receive_messages(AttributeNames=["All"], MaxNumberOfMessages=10)


if __name__ == "__main__":

    url = "https://www.instagram.com/p/CvfMX_qtsyy/"

    worker_input = {
        # mandatory
        "url": url,
        "page_type": "POST",
        #
        # alternative for POST: domain_name + post_identifier
        # "domain_name": "redbubble.com",
        # "post_identifier": "sticker/Three-Sexy-Waifus-in-Lingerie-by-IdaSloan/151694021.EJUG5",
        #
        # meaningful optional
        # "organisation_name": "Chanel_Navee",
        # "upload_id": 999,  # to upd upload_history table
        # "upload_request_id": "tttsss",  # (with upload_id) to upd ss_redis
        # "tags": ["test_tag"],
        # "label": "Counterfeit",
        # "source": "MANUAL_INSERTION"
    }

    try:
        scraping_worker(worker_input)
    except Exception:
        logger.error(f"Worker failed for input: {worker_input}\n{traceback.format_exc()}")
