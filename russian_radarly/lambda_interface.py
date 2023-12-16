import json
import boto3
from enum import Enum

from russian_radarly.exception import RussianRadarlyException, RussianRadarlyTimeout

try:
    # Works when called from the Specific Scraper v1
    from settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
except ModuleNotFoundError:
    try:
        # Works when called from the Specific Scraper v2
        from app.settings import AWS_COUNTERFEIT_ACCESS_KEY_ID as AWS_ACCESS_KEY_ID
        from app.settings import AWS_COUNTERFEIT_SECRET_ACCESS_KEY as AWS_SECRET_ACCESS_KEY
        from app.settings import AWS_REGION
    except (ModuleNotFoundError, ImportError):
        # Works when called from the Counterfeit Platform
        from app.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

lambda_client = boto3.client(
    'lambda',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)


class QueryType(str, Enum):
    GET_POST_DETAILS = 'get_post_details'
    GET_PROFILE_DETAILS = 'get_profile_details'
    GET_PROFILE_DETAILS_FROM_USER_ID = 'get_profile_details_from_user_id'
    GET_PROFILE_POSTS = 'get_profile_posts'
    GET_PROFILE_FOLLOWERS = 'get_profile_followers'
    GET_HASHTAG_POSTS = 'get_hashtag_posts'
    GET_CONSUMPTION_DETAILS = 'get_consumption_details'


def invoke_lambda(payload: dict) -> dict:

    # The account invoking the function must be granted the permission to do so:
    # https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html#permissions-resource-xaccountinvoke
    response = lambda_client.invoke(
        FunctionName='arn:aws:lambda:eu-west-1:977286779374:function:russian-radarly-proxy',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload),
    )

    response_payload = json.loads(response['Payload'].read())

    return response_payload


def call_russian_radarly(
    query_type: QueryType,
    extended_output: bool = False,
    max_attempts: int = 1,
    shortcode: str = None,
    username: str = None,
    hashtag: str = None,
    profile_id: int = None,
    end_cursor: str = None,
    period_start: str = None,
    period_end: str = None,
) -> dict:

    payload = {
        "query_type": query_type._value_,
        "extended_output": extended_output,
        "max_attempts": max_attempts,
        "shortcode": shortcode,
        "username": username,
        "hashtag": hashtag,
        "profile_id": profile_id,
        "end_cursor": end_cursor,
        "period_start": period_start,
        "period_end": period_end,
    }

    lambda_output = invoke_lambda(payload)

    if "successMessage" not in lambda_output:

        error = lambda_output

        if "Task timed out after" in error['errorMessage']:
            raise RussianRadarlyTimeout(error['errorMessage'])

        raise RussianRadarlyException(error)

    return lambda_output["successMessage"]


if __name__ == "__main__":

    output = call_russian_radarly(
        query_type=QueryType.GET_PROFILE_DETAILS, username="therock", max_attempts=2,
    )

    from pprint import pprint
    pprint(output)
