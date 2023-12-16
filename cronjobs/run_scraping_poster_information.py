import json
from collections import defaultdict

from tqdm import tqdm

from app import logger
from app.dao import RedisDAO, WebsiteDAO
from app.service.task_runner.tasks import launch_scraping_task
from app.settings import sentry_sdk

redis_DAO = RedisDAO()
website_DAO = WebsiteDAO()

if __name__ == "__main__":
    logger.input(
        "Getting marketplace posters to recrawl",
        call_name="run_scraping_poster_information",
    )

    posters = redis_DAO.get_posters_info_to_scrape()

    messages_by_ws = defaultdict(list)
    for poster, key in posters:
        domain_name = json.loads(poster)["domain_name"].replace("www.", "")
        if "facebook" not in domain_name and "instagram" not in domain_name:
            messages_by_ws[domain_name].append((json.loads(poster)["poster_url"], key))

    logger.info("Creating task for each website")
    for domain_name in tqdm(messages_by_ws):
        posters = messages_by_ws[domain_name]
        logger.info(f"working with domain_name {domain_name} and {len(posters)} posters")

        ## Save Poster Info In Redis For Processing
        redis_DAO.set_posters_scraping_data(posters, domain_name)

        try:
            website_name = website_DAO.get(domain_name).name
        except Exception as e:
            logger.error("Error on retrieving Website")
            sentry_sdk.capture_exception(e)
            exit()

        scrape_poster_posts = False

        response = launch_scraping_task(
            poster_info_scraping=True,
            website_name=website_name,
            send_to_counterfeit_platform=True,
            scrape_poster_posts=scrape_poster_posts,
        )

        if response is not None:
            logger.info(f"Crawling Poster Info from website {website_name} has been launched")
        else:
            logger.error(f"Error running ecs task to crawl post info for {website_name}")

        for _, key in posters:
            redis_DAO.delete_by_key(key)

    logger.output("Getting marketplace posters to recrawl Completed")
