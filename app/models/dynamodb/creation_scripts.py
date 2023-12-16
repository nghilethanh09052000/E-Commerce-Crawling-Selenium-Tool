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


def exists(table_name):
    """
    Determines whether a table exists. As a side effect, stores the table in
    a member variable.

    :param table_name: The name of the table to check.
    :return: True when the table exists; otherwise, False.
    """
    try:
        table = dynamo_client.Table(table_name)
        table.load()
        exists = True
    except ClientError as err:
        if err.response["Error"]["Code"] == "ResourceNotFoundException":
            exists = False
        else:
            logger.error(
                "Couldn't check for existence of %s. Here's why: %s: %s",
                table_name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise str(err)
    return exists


def create_table(table_name, key_schema, attribute_definitions):
    """
    Creates an Amazon DynamoDB table that can be used to store log data.

    :param table_name: The name of the table to create.
    :return: The newly created table.
    """
    try:
        table = dynamo_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        )
        table.wait_until_exists()
    except ClientError as err:
        logger.error(
            "Couldn't create table %s. Here's why: %s: %s",
            table_name,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise str(err)
    else:
        print("Table creation successful")
        return table


def delete_table(table_name):
    """
    Deletes the table.
    """
    try:
        if not exists(delete_table):
            raise "Table Does not exist"

        table = dynamo_client.Table(table_name)
        table.delete()
    except ClientError as err:
        logger.error(
            "Couldn't delete table. Here's why: %s: %s", err.response["Error"]["Code"], err.response["Error"]["Message"]
        )
        raise str(err)


if __name__ == "__main__":
    table_name = "url_logs"
    ## to delete
    # delete_table(table_name)
    if not exists(table_name):
        print(f"Table: {table_name} does not exist, We will Create it")
        create_table(
            table_name,
            key_schema=[
                {"AttributeName": "url", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "creation_date_timestamp", "KeyType": "RANGE"},  # Sorting Key
            ],
            attribute_definitions=[
                {"AttributeName": "url", "AttributeType": "S"},
                {"AttributeName": "creation_date_timestamp", "AttributeType": "S"},  # S for String
            ],
        )
        print(f"Table: {table_name} Created")
    else:
        print(f"Table: {table_name} already Exists!")
