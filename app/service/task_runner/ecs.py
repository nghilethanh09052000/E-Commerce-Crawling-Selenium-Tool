import traceback
import boto3
from typing import Dict

from app.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_GENERAL_SECURITY_GROUP,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    AWS_SUBNETS,
    ENVIRONMENT_NAME,
)


class TaskNotLaunched(Exception):
    pass


client = boto3.client(
    "ecs",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def create_ecs_container(command, started_by_sentence, task_revision=12, tags: Dict[str, str] = {}):
    """Create a Fargate task to run the scraping task

    Note: task_revision determine the instance size used, 2 correspond to the default one
    """

    try:
        subnets = AWS_SUBNETS
        security_groups = AWS_GENERAL_SECURITY_GROUP  # Navee Security Group

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecs.html#ECS.Client.run_task
        response = client.run_task(
            cluster="specific-scraper",
            count=1,
            enableECSManagedTags=True,
            enableExecuteCommand=True,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnets,
                    "securityGroups": security_groups,
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": "specific-scraper-production",
                        "command": command,
                        "environment": [{"name": "ENVIRONMENT_NAME", "value": ENVIRONMENT_NAME}],
                    }
                ]
            },
            # Specify the startedBy tag to display it in the cluster's tasks list
            startedBy=started_by_sentence,
            taskDefinition=f"specific-scraper:{task_revision}",
            tags=[{"key": str(key), "value": str(value)} for key, value in tags.items()],
        )

    except Exception as e:
        traceback.print_tb(e.__traceback__)
        response = None

        raise TaskNotLaunched("An exception occurred when trying to create an ECS scraping task (check CloudWatch)")

    return response
