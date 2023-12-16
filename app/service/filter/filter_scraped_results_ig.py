from typing import Optional

from app.api.logo_detection import get_brands_from_image_url
from app.dao import OrganisationDAO, SearchDAO
from app.helpers.utils import load_instagram_search_configs
from app.models import Organisation
from app.service.filter.utils import filter_by_exclude_keywords, filter_by_must_have_keywords

organisation_DAO = OrganisationDAO()
search_DAO = SearchDAO()


def select_instagram_profiles(scraped_posters: dict):
    """Select the profiles to be sent to the Counterfeit Platform depending on the scraping settings

    Args:
        scraped_posters (dict): The profiles which have been saved in database

    Returns:
        [{"username": username, "profile_object": Profile}]: The details of the posts selected for being sent to the Counterfeit Platform
    """

    return [
        {"username": username, "profile_object": profile_object} for username, profile_object in scraped_posters.items()
    ]


def filter_ig_scraped_results(
    scraped_post_by_ids: dict,
    organisation: Optional[Organisation],
) -> list:
    """Select the posts to be sent to the Counterfeit Platform depending on the scraping settings

    Parameters:
    ===========
    scraped_post_by_ids: dict
        dictionary describing the posts which have been saved in database
    organisation: Organisation or None
        determines to which organisation we are sending the posts if the cross brand search is disabled

    Returns:
    ========
    posts_to_send: dict[]
        list containing the details of the posts selected for being sent to the Counterfeit Platform
        [{"shortcode": shortcode, "post_object": Post, "organisation_name": organisation_name, "post_tag": None}]
    """
    if not scraped_post_by_ids:
        return []

    if not organisation:
        posts_to_send = dispatch_among_organisations_using_logo(scraped_post_by_ids=scraped_post_by_ids)
        return posts_to_send

    posts_to_send = [post["post_object"].serialize_full for post in scraped_post_by_ids.values()]

    if organisation.exclude_keywords:
        posts_to_send = filter_by_exclude_keywords(
            posts=posts_to_send,
            exclude_keywords=organisation.exclude_keywords.split(","),
        )

    if organisation.must_have_keywords:
        posts_to_send = filter_by_must_have_keywords(
            posts=posts_to_send,
            must_have_keywords=organisation.must_have_keywords.split(","),
        )

    post_ids_to_send = [post["platform_id"] for post in posts_to_send]

    return [
        {
            "shortcode": post_id,
            "post_object": post["post_object"],
            "organisation_name": organisation.name,
            "tags": post["tags"],
        }
        for post_id, post in scraped_post_by_ids.items()
        if post_id in post_ids_to_send
    ]


def dispatch_among_organisations_using_logo(scraped_post_by_ids: dict) -> list:
    instagram_search_configs = load_instagram_search_configs()
    posts_to_send = []

    logo_prediction_per_image_url = get_brands_from_image_url(
        [picture for post in scraped_post_by_ids.values() for picture in post["post_object"].pictures]
    )

    # In this part, we first check if we can detect logos in the images of the post
    # If a logo is detected, we send the post to the brand of that logo
    # If multi logos are detected, we send the post to all the brands detected
    # If no logo detected, we use the search configs of all the brands to know which ones to send the post to
    # This step is factorized (one search for multiple accounts instead of one search per account)
    # to run less database intensive full text queries
    post_without_logo = dict()

    # Iterate through the posts, and check if we can find a logo for any known brands
    for shortcode, post in scraped_post_by_ids.items():
        if post.get("skip_filter_scraped_results"):
            for organisation_name in post["valid_organisations"]:
                posts_to_send.append(
                    {
                        "shortcode": shortcode,
                        "post_object": post["post_object"],
                        "organisation_name": organisation_name,
                        "tags": post["tags"],
                    }
                )
            continue

        brands = set()
        for picture_url in post["post_object"].pictures:
            brands.update(logo_prediction_per_image_url[picture_url])

        if not brands:
            post_without_logo[shortcode] = post["post_object"]
            continue

        # for each brand found, we append a post to send
        for brand in brands:
            posts_to_send.append(
                {
                    "shortcode": shortcode,
                    "post_object": post["post_object"],
                    "organisation_name": brand,
                }
            )

    # Iterate through instagram_search_configs for the posts where no logo was detected
    for config_organisation_name, config in instagram_search_configs.items():
        # Check if one or several posts match the brand identification query
        if config_organisation_name == "Commons":
            continue

        # Use the brand identification query to check whether the brand is mentioned
        query = config["brand_identification_query"]

        selected_post_ids = search_DAO.db_search(
            post_without_logo,
            query,
        )

        new_posts_to_send = [
            {
                "shortcode": shortcode,
                "post_object": post_object,
                "organisation_name": config_organisation_name,
            }
            for shortcode, post_object in post_without_logo.items()
            if post_object.id in selected_post_ids
        ]
        posts_to_send += new_posts_to_send

    return posts_to_send
