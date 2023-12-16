"""This script launches all the scraping tasks which need to be run (scraping_interval exceeded since last_run_time)"""
from app import logger
import sys
from datetime import datetime

import boto3
from app.dao import TaskDAO
from app.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    sentry_sdk,
)
from tqdm import tqdm

task_DAO = TaskDAO()

client = boto3.client(
    "ecs",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

if __name__ == "__main__":
    try:
        logger.input("Start Cronjob to check fargate tasks running for too long")

        logger.info("Getting all active tasks")
        stop_running_tasks = False
        next_token = None
        complete_tasks_running_too_long = []
        complete_db_task_ids_running_too_long = []
        id_list = []
        while stop_running_tasks == False:
            active_tasks = client.list_tasks(
                cluster="specific-scraper",
                launchType="FARGATE",
                desiredStatus="RUNNING",
                nextToken="" if next_token is None else next_token,
            )

            if not active_tasks or len(active_tasks.get("taskArns", [])) < 1:
                logger.info("No active tasks running")
                sys.exit()

            now = datetime.now()
            # get active task ids
            task_list = active_tasks.get("taskArns")
            next_token = active_tasks.get("nextToken", None)

            # get active task information from ids
            task_information = client.describe_tasks(cluster="specific-scraper", tasks=task_list)

            if task_information is None or len(task_information.get("tasks", [])) < 1:
                logger.info("Error getting task information")
                sys.exit()

            tasks_running_too_long = []
            db_task_ids_running_too_long = []

            for task in tqdm(task_information["tasks"]):
                ecs_task_id = task.get("taskArn")
                started_on = task.get("createdAt", "startedAt").replace(tzinfo=None)
                max_task_duration = 1
                task_duration_in_days = (now - started_on).days
                started_by = task.get("startedBy")

                # Scrape the ID of the task object in database if the task has been launched with a task ID
                try:
                    db_task_id_str = started_by.split("task ")[1]
                    assert db_task_id_str.isdigit()
                    db_task_id = int(db_task_id_str)
                    # Retrieve the corresponding task object in database
                    task = task_DAO.get(db_task_id)
                    assert task.config_file != "instagram_hashtag_search"
                except Exception:
                    ## Check if its a scraping posters task
                    db_task_id = started_by
                # Don't scrape the tasks which correspond to Instagram keyword search (can legit take more than a day)

                # if task has been running for more than 1 day
                if task_duration_in_days >= max_task_duration:

                    # add details to report to Sentry
                    tasks_running_too_long.append(task)
                    db_task_ids_running_too_long.append(db_task_id)

                    # stop task
                    response = client.stop_task(
                        cluster="specific-scraper",
                        task=ecs_task_id,
                        reason="Task running for more than one day",
                    )
                    if response is None:
                        sentry_sdk.capture_message(f"Unable to delete task {db_task_id} started on {started_on}")
                    else:
                        logger.info(f"Task {db_task_id} successfully stopped")

            if tasks_running_too_long:
                complete_tasks_running_too_long.extend(tasks_running_too_long)

            if db_task_ids_running_too_long:
                complete_db_task_ids_running_too_long.extend(db_task_ids_running_too_long)

            if next_token is None:
                stop_running_tasks = True

        # Return sentry error
        if len(tasks_running_too_long) > 0:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error-type", "ecs-task-delay")
                scope.set_extra("tasks", tasks_running_too_long)
                scope.set_extra("tasks_ids", db_task_ids_running_too_long)
                sentry_sdk.capture_message("ECS Tasks Took too long")
        else:
            logger.info("No tasks to stop")

    except Exception as ex:
        print(ex)
        # sentry_sdk.capture_message(ex)

    logger.output("Cronjob Complete")
