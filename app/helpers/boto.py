import boto3
from app.settings import AWS_ACCESS_KEY_ID, AWS_REGION, AWS_SECRET_ACCESS_KEY


ecs_client = boto3.client(
    "ecs",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def get_active_website_tasks_count():
    """Count the number of active tasks per domain"""

    active_tasks_arn = ecs_client.list_tasks(cluster="specific-scraper", desiredStatus="RUNNING")

    active_tasks = ecs_client.describe_tasks(cluster="specific-scraper", tasks=active_tasks_arn.get("taskArns", []))

    active_website_tasks = [t["startedBy"].replace("Scraping Poster Posts for ", "") for t in active_tasks["tasks"]]

    active_website_tasks_count = {item: active_website_tasks.count(item) for item in active_website_tasks}

    return active_website_tasks_count
