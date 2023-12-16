from app import logger
import boto3
from botocore.exceptions import ClientError

from app.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

dynamo_client = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)


class LogDAO:
    def __init__(self):
        """
        :param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.table = dynamo_client.Table("url_logs")

    def add(self, url: str, creation_date_timestamp: str, payload: str):
        """
        Adds a log to the table.

        :param url: The url
        :param payload: Data collected on payload
        """
        try:
            self.table.put_item(
                Item={"url": url, "creation_date_timestamp": creation_date_timestamp, "payload": payload}
            )

        except ClientError as err:
            logger.error(
                f"Couldn't add log {url} to table {self.table.name}. Here's why: {err.response['Error']['Code']}: {err.response['Error']['Message']}",
            )
            raise

    def get_url(self, url: str, creation_date_timestamp: str):
        """
        Gets url data from the table for a specific url.

        :param url: The url
        :param payload: Data collected on payload
        """
        try:
            response = self.table.get_item(Key={"url": url, "creation_date_timestamp": creation_date_timestamp})
        except ClientError as err:
            logger.error(
                f"Couldn't get log {url} to table {self.table.name}. Here's why: {err.response['Error']['Code']}: {err.response['Error']['Message']}",
            )
            raise
        else:
            return response["Item"]
