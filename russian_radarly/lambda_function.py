import json
import logging
import sys
from time import sleep

from exception import RussianRadarlyException
from controller import RequestController
from enumerator import QueryType
from rr_settings import sentry_sdk

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def scrape(request_controller, event, max_attempts):

    for i in range(1, max_attempts + 1):
        try:

            if request_controller.query_type == QueryType.GET_POST_DETAILS:
                output = request_controller.scrape_ig_post_from_shortcode(event['shortcode'])

            elif request_controller.query_type == QueryType.GET_PROFILE_DETAILS:
                output = request_controller.scrape_ig_profile_details_from_username(event['username'])

            elif request_controller.query_type == QueryType.GET_PROFILE_DETAILS_FROM_USER_ID:
                output = request_controller.scrape_ig_profile_details_from_user_id(event['profile_id'])

            elif request_controller.query_type == QueryType.GET_PROFILE_POSTS:
                output = request_controller.scrape_ig_posts_from_profile(event['profile_id'], event['end_cursor'])

            elif request_controller.query_type == QueryType.GET_PROFILE_FOLLOWERS:
                output = request_controller.scrape_ig_followers_from_profile(event['profile_id'], event['end_cursor'])

            elif request_controller.query_type == QueryType.GET_HASHTAG_POSTS:
                output = request_controller.scrape_ig_posts_from_hashtag(event['hashtag'], event['end_cursor'])

            elif request_controller.query_type == QueryType.GET_CONSUMPTION_DETAILS:
                output = request_controller.get_consumption_details(event.get('period_start'), event.get('period_end'))

            return output

        except Exception as e:
            if i < max_attempts:
                logger.error(f"Exception during {i}/{max_attempts} attempt {repr(e)} | event: {event}")
                sleep(2)
                continue
            raise e


def lambda_handler(event, context):
    logger.info(f'event: {event}')
    query_type = QueryType(event["query_type"])
    request_controller = RequestController(query_type, event.get('extended_output', False))
    try:
        output = scrape(request_controller, event, event.get("max_attempts", 1))
    except Exception as e:
        logger.error(f"faieled to scrape: {event} | error: {repr(e)}")
        sentry_sdk.capture_exception(e)
        return {"errorMessage": repr(e)}
    return {"successMessage": output}


if __name__ == "__main__":

    event = {
        'query_type': 'get_profile_details',
        'shortcode': None,
        'username': 'markatrend2020',
        'hashtag': None,
        'profile_id': '1398658797',
        'end_cursor': None,
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_post_details',
        'shortcode': 'CeXisPwrV4P',
        'extended_output': True,
        'username': None,
        'hashtag': None,
        'profile_id': '232192182',
        'end_cursor': 'QVFBT1QzcWxkRDRQYVZ3a1VoNFl6TlNzYkw0NXBaSVROazdvU1pOWm5meTFReDM2aHVjVW83Y2dGY1BfX1h1VUU0U3lGUHVTclhSN2xYN3gxdjZXci1nOA==',
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_hashtag_posts',
        'shortcode': None,
        'username': None,
        'hashtag': 'saab900',
        'profile_id': None,
        'end_cursor': None,
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_hashtag_posts',
        'shortcode': None,
        'username': None,
        'hashtag': 'saab900',
        'profile_id': None,
        'end_cursor': 'QVFDWG5XWjU0RHdKdERBUDFoN3hTZG8wMDJnSFNpaFFocGhQcUQyRFh2Ni1IMDNSekJXV2JMOE95SDdPdFp1ZTV6d3BOaHB2b1JYdTFGYWpGUWJvRlBERw==',  # noqa:E501
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_profile_details',
        'shortcode': None,
        'username': 'larocheposay',
        'hashtag': None,
        'profile_id': None,
        'end_cursor': None,
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_profile_details_from_user_id',
        'shortcode': None,
        'username': None,
        'hashtag': None,
        'profile_id': '450284584',
        'end_cursor': None,
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_profile_posts',
        'shortcode': None,
        'username': None,
        'hashtag': None,
        'profile_id': '450284584',
        'end_cursor': None,
        'period_start': None,
        'period_end': None,
    }

    event = {
        'query_type': 'get_consumption_details',
        'shortcode': '',
        'username': '',
        'hashtag': '',
        'profile_id': '',
        'end_cursor': '',
        'period_start': '2022-10-12',
        'period_end': '2022-11-12',
    }

    event = {
        'query_type': 'get_post_details',
        'shortcode': 'Bz5blRtn5W_',
        'extended_output': True,
        'max_attempts': 3,
        'username': None,
        'hashtag': None,
        'profile_id': None,
        'end_cursor': None,
        'period_start': None,
        'period_end': None,
    }

    output = lambda_handler(event, None)

    from pprint import pprint
    pprint(output)
