"""This script runs posts recrawling"""
import json
from collections import defaultdict
from app import logger
from app.dao import RedisDAO, WebsiteDAO
from app.service.task_runner.tasks import launch_scraping_task
from app.settings import sentry_sdk

redis_DAO = RedisDAO()
website_DAO = WebsiteDAO()

if __name__ == "__main__":

    logger.input("Getting RISE posts to recrawl", call_name="run_scraping_poster_information")
    posts = redis_DAO.get_posts_recrawling()

    logger.info("Sorting posts by domain")
    messages_by_ws = defaultdict(list)
    for post, key in posts:
        domain_name = json.loads(post)["domain_name"].replace("www.", "")
        messages_by_ws[domain_name].append((post, key))

    logger.info("Creating tasks for each websites")
    for domain_name in messages_by_ws:
        posts = messages_by_ws[domain_name]

        try:
            website_name = website_DAO.get(domain_name).name
        except Exception as e:
            logger.error(f"Error on retrieving Website {domain_name}")
            sentry_sdk.capture_exception(e)
            continue

        redis_DAO.set_post_scraping_data(posts, domain_name)

        response = launch_scraping_task(from_rise=True, website_name=website_name)

        if response is not None:
            logger.info(f"Recrawling for websites {website_name} has been launched")
        for _, key in posts:
            redis_DAO.delete_by_key(key)
