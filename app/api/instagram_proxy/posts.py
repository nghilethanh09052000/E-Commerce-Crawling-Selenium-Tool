from russian_radarly.lambda_interface import (
    RussianRadarlyException,
    QueryType,
    RussianRadarlyTimeout,
    call_russian_radarly,
)
from app.settings import sentry_sdk


def get_post_multithreading(shortcode: str):
    """This function is meant to be used in a multithreading context"""

    try:
        return call_russian_radarly(
            query_type=QueryType.GET_POST_DETAILS,
            shortcode=shortcode,
            extended_output=True,
            max_attempts=2,
        )
    except (RussianRadarlyException, RussianRadarlyTimeout) as e:
        sentry_sdk.capture_exception(e)
        return
