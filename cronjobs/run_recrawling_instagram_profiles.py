from uuid import uuid4
from app.models.enums import ScrapingType
from app import logger
from app.dao import RedisDAO
from app.helpers.utils import chunks
from app.service.task_runner.tasks import launch_scraping_task
from app.settings import PROFILES_BATCH_SIZE, sentry_sdk

redis_DAO = RedisDAO()


if __name__ == "__main__":

    # Build a list of tuples associating each user object with its Redis key
    users_keys = redis_DAO.get_instagram_profiles_to_recrawl()

    # Capture a Sentry message when the batch starts to get handled
    with sentry_sdk.push_scope() as scope:
        scope.set_extra("keys", users_keys)
        scope.set_extra("keys length", len(users_keys))
        sentry_sdk.capture_message("Launched Instagram profile recrawling requests")

    # Send the crawling tasks by batch
    for users_keys_batch in chunks(users_keys, PROFILES_BATCH_SIZE):

        batch_key = f"ig_users_batch:{uuid4()}"

        redis_DAO.set_instagram_profile_batch(users_keys_batch, batch_key)

        response = launch_scraping_task(
            scraping_type=ScrapingType.POSTER_SEARCH,
            website_name="instagram.com",
            scrape_poster_posts=True,
            send_to_counterfeit_platform=True,
            ig_users_batch_name=batch_key,
        )

        if response is None:
            # Task not launched
            redis_DAO.delete_by_key(batch_key)
        else:
            logger.info(f"The crawling of {len(users_keys_batch)} profiles has been launched")

            for _, key in users_keys_batch:
                redis_DAO.delete_by_key(key)
