from app import logger
from app.service.send import send_scraping_task
from app.settings import sentry_sdk
from app.dao.redis import RedisDAO


OBJ_TYPES = (
    ("posts", "POST"),
    ("accounts", "POSTER"),
)
redis_DAO = RedisDAO()


def translate_request_to_task_list(upload_key, request):
    tasks = []
    task_template = {
        "source": "MANUAL_INSERTION",
        "upload_request_id": upload_key,
    }
    if request.get("organisation_name"):
        task_template["organisation_name"] = request.get("organisation_name")
    for obj_type, page_type in OBJ_TYPES:
        if obj_type not in request:
            continue
        task_template["page_type"] = page_type
        for obj in request[obj_type]:
            if not obj.get("url"):
                continue
            task = task_template.copy()
            for k in ("url", "tags", "label", "upload_id"):
                if v := obj.get(k):
                    task[k] = v
            tasks.append(task)
    return tasks


if __name__ == "__main__":
    logger.input("start run_scraping_upload_requests", call_name="run_scraping_upload_requests")
    # If the hset "running" is not empty and there are no upload_request keys, report abnormality and clean "running"
    # This guarantees that "running", for which we can't set an expiry time, can't grow too big with dead keys
    running_hset_exists = redis_DAO.exists("running")
    upload_keys = redis_DAO.get_upload_requests()

    if running_hset_exists and not upload_keys:
        redis_DAO.delete_by_key("running")

    # Retrieve all the keys which begin with "upload_request:"
    for upload_key in upload_keys:
        logger.info(f"working on upload request {upload_key}")
        running_status = redis_DAO.get_upload_running_status(upload_key)
        if running_status:
            logger.info("Upload request is running, skip")
            continue

        upload_request = redis_DAO.get_upload_request(upload_key)
        logger.info(f"upload request {upload_request}")

        tasks = translate_request_to_task_list(upload_key, upload_request)
        if not tasks:
            logger.info(f"no valid tasks {upload_key}")
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("upload-request", upload_request)
                sentry_sdk.capture_message("no valid tasks in upload request")
            continue
        for task in tasks:
            send_scraping_task(task)

        redis_DAO.set_upload_running_status(upload_key)
        logger.info(f"finished working on upload request {upload_key}")
    logger.output("finish run_scraping_upload_requests")
