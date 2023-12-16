from typing import List, Optional
from datetime import datetime

from russian_radarly.lambda_interface import (
    RussianRadarlyException,
    QueryType,
    RussianRadarlyTimeout,
    call_russian_radarly,
)

from app import logger, sentry_sdk
from automated_moderation.dataset import BasePost, BaseImage, BasePoster, BaseWebsite


def get_light_posts_from_hashtag(
    hashtag: str, max_posts_to_browse: int, max_posts_per_hashtag: int = 500, max_attempts: Optional[int] = 3
) -> List[BasePost]:
    """Retrieve the previews of Instagram posts corresponding to a hashtag (info not as detailed as when retrieving a complete post)"""

    # The hashtag must be a non empty lowercase stripped string
    assert hashtag.lower().strip() and hashtag == hashtag.lower().strip()

    light_posts = []
    has_next_page = True
    end_cursor = ""
    attempt = 1

    # Retrieve more posts until there are no more posts available or the maximum number we want to retrieve is reached
    while has_next_page and len(light_posts) < min(max_posts_to_browse, max_posts_per_hashtag):

        try:

            page = call_russian_radarly(
                QueryType.GET_HASHTAG_POSTS,
                hashtag=hashtag,
                end_cursor=end_cursor,
                max_attempts=max_attempts if max_attempts else 3,
            )

            # The posts are retrieved 36 at a time
            light_posts += [
                BasePost(
                    id=post_dict["shortcode"],
                    images=[BaseImage(url=picture_url) for picture_url in post_dict["pictures"]],
                    poster=BasePoster(id=post_dict["owner"]["id"]),
                    created_at=datetime.strptime(post_dict["publication_datetime"], "%Y-%m-%d %H:%M:%S"),
                    description=post_dict["caption"],
                    search_query=hashtag,
                    website=BaseWebsite(domain_name="instagram.com", website_category="Social Media"),
                )
                for post_dict in page["media"]["posts"]
            ]

            end_cursor = page["media"]["page_info"]["end_cursor"]
            has_next_page = page["media"]["page_info"]["has_next_page"]

        except (RussianRadarlyException, RussianRadarlyTimeout):

            if max_attempts is not None or attempt > 100:
                break
            attempt += 1

        except Exception as e:
            logger.error(e)
            sentry_sdk.capture_exception(e)
            break

    return light_posts[:max_posts_to_browse]
