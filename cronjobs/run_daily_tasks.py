"""This script launches all the scraping tasks which need to be run:
   - scraping_interval exceeded since last_run_time
"""
from datetime import datetime
from collections import defaultdict
import re
import math

from app import logger, sentry_sdk
from app.dao import TaskDAO
from app.models.enums import ScrapingType
from app.service.task_runner.tasks import launch_scraping_task
from app.service.send_post import count_posts_sent_this_month


# Normally these work as "limit per 15mins" as the cronjob runs every 15mins.
# A precise time-based implementation of limits would also require analyzing running tasks,
# so for now I'll just do "limit per one run of run_daily_tasks.py".
# If someone runs the script manually, it'll boost the limit, but it may be desirable.
def get_limit_per_domain(domain_name):
    if domain_name == "shopee":
        return 4

    if domain_name == "instagram.com":
        return 25

    return 1


task_DAO = TaskDAO()

logger.input("Launch Cronjob Run Daily Tasks")
tasks_to_run = task_DAO.get_tasks_to_run(ignore_interval=False)

# We run scheduling every 15 minutes, see terraform/ecs_run_daily_tasks.tf
# We allow up to 20% boost over the ideal rate of tasks started.
# Remaining tasks will be delayed until subsequent runs of the scheduling
# script to distribute the load more evenly.
max_tasks_per_run = math.ceil(task_DAO.avg_task_count_per_interval(60 * 15) * 1.2)

logger.info(f"There are {len(tasks_to_run)} tasks to run with global limit of {max_tasks_per_run}")
now = datetime.now()

counter_by_domain = defaultdict(int)
skipped = 0
started = 0
for task in list(tasks_to_run):
    if started >= max_tasks_per_run:
        skipped += 1
        logger.warn(f"SKIPPING task {task.id} because the global limit of {max_tasks_per_run} task per run is exceeded")
        continue

    if task.organisation:
        max_posts_by_month, posts_sent_this_month = count_posts_sent_this_month(organisation=task.organisation)
        print(
            f"max_posts_by_month={max_posts_by_month}, posts_sent_this_month={posts_sent_this_month}, organisation={task.organisation.name}"
        )
        if posts_sent_this_month >= max_posts_by_month:
            skipped += 1
            logger.warn(f"SKIPPING task {task.id} because max_posts_by_month is exceeded for {task.organisation.name}")
            continue

    domain_name = task.website.domain_name
    task_descr = f"({task.id}, {domain_name}, {task.organisation_id})"
    logger.info(f"Going to launch task {task_descr}")
    counter_by_domain[domain_name] += 1
    if re.search("shopee", domain_name):
        domain_name = "shopee"

    domain_limit = get_limit_per_domain(domain_name)
    if counter_by_domain[domain_name] > domain_limit:
        skipped += 1
        logger.info(f"SKIPPING {task_descr} task because per-domain limit of {domain_limit} is exceeded")
        continue

    try:
        response = launch_scraping_task(
            scraping_type=ScrapingType.POST_SEARCH_COMPLETE,
            task_id=task.id,
            website_name=task.website.name,
            organisation_name=task.organisation and task.organisation.name,
            task_revision=task.task_revision,
        )

        if response is None:
            raise ValueError("no response from launch_scraping_task")

        logger.info(f"ECS response: {response}")
        started += 1
        logger.info(f"Task {task_descr} has been launched")

    except Exception as e:
        logger.error(f"During launching task {task_descr} : {repr(e)}")
        sentry_sdk.capture_exception(e)


logger.output(
    f"Launch Cronjob Run Daily Tasks Completed. Total: {len(tasks_to_run)}/{max_tasks_per_run}, started: {started}, skipped: {skipped}"
)
