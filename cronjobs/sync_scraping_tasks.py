"""This script maintains a list of running tasks on redis for backend syncing with specific scraper"""

import json
from sqlalchemy import distinct, and_

from app import logger
from app.models import Session, Task, Website, Organisation
from app.settings import (
    redis,
    sentry_sdk,
)


def update_tracked_domains():
    domains = get_actual_tracked_domain_names()
    push_domains_to_redis(domains)


def get_actual_tracked_domain_names():
    with Session() as session:
        domains = set(x[0] for x in session.query(distinct(Website.domain_name)).all())
    assert len(domains) > 0, "number of domains is expected to be > 0"
    return domains


def push_domains_to_redis(domains):
    domains_str = json.dumps(list(domains))
    redis.set("tracked_domains", domains_str)


if __name__ == "__main__":

    logger.input("Start Cronjob to update list of available tasks")

    try:
        """
        Returns the logs for all the tasks that run for each organisation.
        """

        with Session() as session:
            results = (
                session.query(
                    Task.id, Organisation.name.label("organisation_name"), Website.domain_name, Website.country_code
                )
                .join(Website, Website.id == Task.website_id)
                .join(Organisation, Organisation.id == Task.organisation_id)
                .filter(and_(Task.is_active == True, Website.is_active == True))
                .all()
            )

        logger.info(f"{len(results)} tasks found! ")

        data = []
        for task in results:
            data.append(
                {
                    "task_id": task.id,
                    "domain_name": task.domain_name,
                    "organisation_name": task.organisation_name,
                    "country_code": task.country_code,
                }
            )

        if len(data) > 0:
            key = "sync_scraping_tasks"
            TASKS_EXPIRY = 3600 * 24 * 6  # 6 days
            redis.set(key, json.dumps(data))
            redis.expire(key, TASKS_EXPIRY)
            logger.info("Redis updated with list of available tasks")
        else:
            logger.error("No Tasks Found")

    except Exception as ex:
        print(ex)
        sentry_sdk.capture_message(ex)

    try:
        update_tracked_domains()
        logger.info("Redis updated with list of tracked domain names")
    except Exception as ex:
        print(ex)
        sentry_sdk.capture_message(ex)

    logger.output("Cronjob Complete")
