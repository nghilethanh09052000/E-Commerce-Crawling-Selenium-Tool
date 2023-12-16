"""This script launches all the scraping tasks to get poster posts"""
import json
from tqdm import tqdm

from app.settings import sentry_sdk
from app import logger
from app.helpers.boto import get_active_website_tasks_count
from app.dao import RedisDAO, WebsiteDAO
from app.service.task_runner.tasks import launch_scraping_task

redis_DAO = RedisDAO()
website_DAO = WebsiteDAO()

if __name__ == "__main__":
    logger.input("Getting marketplace posters posts", call_name="run_scraping_poster_posts")

    posters = redis_DAO.get_posters_posts_to_scrape()

    # get active scrapers to avoid running multiple scraping for same domain
    active_website_tasks_count = get_active_website_tasks_count()

    logger.info("Creating task for each poster")
    for poster, key in tqdm(posters):
        domain_name = json.loads(poster)["domain_name"].replace("www.", "")
        poster_url = json.loads(poster)["poster_url"]
        if "facebook" in domain_name or "instagram" in domain_name:
            continue

        try:
            website_name = website_DAO.get(domain_name).name
        except Exception as e:
            logger.error("Error on retrieving Website")
            sentry_sdk.capture_exception(e)
            exit()

        #
        if website_name not in active_website_tasks_count:
            active_website_tasks_count[website_name] = 1
        elif active_website_tasks_count[website_name] > 1:
            logger.info(f"Another task is still running for this {website_name} try again later")
            continue
        else:
            active_website_tasks_count[website_name] += 1

        response = launch_scraping_task(
            poster_posts_scraping=True,
            poster_url=poster_url,
            website_name=website_name,
            send_to_counterfeit_platform=True,
        )

        if response is not None:
            logger.info(f"Crawling Poster Posts from website {website_name} has been launched")
        else:
            logger.error(f"Error launching task to crawl post posts for{website_name}")

        redis_DAO.delete_by_key(key)
