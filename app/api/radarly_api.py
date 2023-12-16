import re
from datetime import datetime
from typing import List, Union, Optional

from radarly.constants import PLATFORM
from radarly.exceptions import RadarlyHTTPError
from radarly.parameters import SearchPublicationParameter as Payload
from radarly.project import Project
from tqdm import tqdm

from app import logger, sentry_sdk
from automated_moderation.dataset import BasePost, BaseImage, BasePoster, BaseWebsite


# Retrieve the Radarly project, dashboard and queries we are using
try:
    project = Project.find(pid=5276)
except (RadarlyHTTPError, ConnectionError):
    project, dashboard = None, None
except Exception:
    sentry_sdk.capture_exception()
    project, dashboard = None, None


def retrieve_radarly_publications(
    query_label,
    start_date,
    end_date=datetime.now(),
    domain_name=None,
    post_identifier_regex=None,
) -> List[BasePost]:
    """Retrieve publications from Radarly using their API

    Args:
        query_label (str): name of the query saved in the Radarly project
        start_date (datetime.datetime): start of the publications retrieval date range
        end_date (datetime.datetime): end of the publications retrieval date range
        website_name (str or None): "instagram.com" OR "facebook.com" OR None (if website_name is None, we search both platforms)
        post_identifier_regex (str)

    Returns:
        posts (dict[]): a list of dictionaries containing the available and useful information on a social media post
    """

    focus = next((f for f in project.focuses if f.label == query_label), None)

    if not focus:
        logger.warn(f"The query label '{query_label}' does not correspond to any focus")

    # Retrieve publications
    search_parameters = (
        Payload().pagination(start=0, limit=100).publication_date(start_date, end_date).focuses(include=[focus.id])
    )

    if domain_name == "instagram.com":
        search_parameters = search_parameters.platforms(PLATFORM.INSTAGRAM)
    elif domain_name == "facebook.com":
        search_parameters = search_parameters.platforms(PLATFORM.FACEBOOK)
    else:
        search_parameters = search_parameters.platforms(PLATFORM.FACEBOOK, PLATFORM.INSTAGRAM)

    posts = []

    # The publications are scraped from the most recent to the oldest
    # Sometimes, the retrieval fails because of a Radarly error for a single publication
    # In case of a crash, we retrieve the next oldest publication and try with this date as the new end_date
    while end_date:
        search_parameters = search_parameters.publication_date(start_date, end_date)
        new_posts, end_date = retrieve_publications_from_search_parameters(search_parameters, post_identifier_regex)
        posts += new_posts

    return posts


def retrieve_publications_from_search_parameters(
    search_parameters, post_identifier_regex
) -> Union[List[BasePost], Optional[datetime]]:
    """Retrieve publications from Radarly using their API. The publications are scraped from the most recent to the oldest.

    Args:
        search_parameters (Radarly Payload object)
        post_identifier_regex (str)

    Returns:
        posts (dict[]): a list of dictionaries containing the available and useful information on a social media post
        oldest_publication_date (datetime or None): date of publication of the oldest publication successfully scraped for the current search parameters; None if all the publications are successfully scraped
    """

    # Build a generator which yields publications
    all_publications = project.get_all_publications(search_parameters)

    posts = []
    oldest_publication_date = None

    try:

        for publication in tqdm(all_publications, total=all_publications.total):

            pictures = None
            if publication.media:
                pictures = publication.media["image"]

            if not pictures:
                continue

            if not publication.permalink:
                continue

            oldest_publication_date = publication.date
            posts.append(
                BasePost(
                    id=re.search(post_identifier_regex, publication.permalink).group(1)
                    if post_identifier_regex
                    else None,
                    created_at=publication.date,
                    url=publication.permalink,
                    description=publication.text,
                    poster=BasePoster(name=publication.user["screen_name"]),
                    images=[BaseImage(url=url) for url in pictures],
                    search_query="radarly",
                    website=BaseWebsite(domain_name="instagram.com", website_category="Social Media"),
                )
            )

        # We don't return the oldest publication date when the scraping has been successful for all the publications
        return posts, None

    except RadarlyHTTPError:
        return posts, oldest_publication_date


if __name__ == "__main__":

    from datetime import datetime

    query = "Chanel"

    range_start = datetime(2021, 9, 6)
    range_end = datetime(2021, 9, 7)

    posts = retrieve_radarly_publications(query, range_start, range_end)

    urls = [post.url for post in posts]

    print(f"{query}: {len(urls)} posts")
