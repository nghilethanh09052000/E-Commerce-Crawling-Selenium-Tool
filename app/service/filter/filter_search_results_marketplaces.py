from typing import List, Optional
import random

from automated_moderation.dataset import BasePost, BaseOrganisation, BaseImage, BaseWebsite
from app import logger, sentry_sdk
from app.dao import OrganisationDAO, PostDAO
from app.service.filter.utils import prefiltering_predictions, dispatch_among_organisations
from app.helpers.translation import translate_posts
from app.api.logo_detection import get_logo_prediction
from app.models import Organisation, Website
from app.service.filter.utils import filter_by_exclude_keywords, FILTERING_RATE
from app.models.enums import ScrapingStatus


MARKETPLACE_FILTERING_ORG = []

organisation_DAO = OrganisationDAO()
post_DAO = PostDAO()


def get_filtering_threshold(organisation: Organisation) -> Optional[float]:
    if organisation.name == "Zagtoon":
        return 0.7

    if organisation.name in ["Brunello_Cucinelli", "Fred"]:
        return 0

    if organisation.activate_filtering:
        return 0.2

    return None


def filter_marketplace_search_results(
    light_post_by_ids: dict, organisation: Optional[Organisation], website: Website, sample: bool
) -> dict:
    if not light_post_by_ids:
        return {}

    if not organisation:
        posts_to_scrape = dispatch_among_organisations(list(light_post_by_ids.values()))
        posts_to_scrape_by_ids = {post["id"]: post for post in posts_to_scrape}
        return posts_to_scrape_by_ids

    if organisation.exclude_keywords:
        posts_to_scrape = filter_by_exclude_keywords(
            posts=light_post_by_ids.values(),
            exclude_keywords=organisation.exclude_keywords.split(","),
        )
        light_post_by_ids = {post["id"]: post for post in posts_to_scrape}

    posts_to_scrape_by_ids = filter_by_risk_score_safe(
        light_post_by_ids=light_post_by_ids,
        organisation=organisation,
        website=website,
        sample=(False if not organisation.activate_filtering else sample),
    )

    return posts_to_scrape_by_ids


def filter_by_risk_score_safe(
    light_post_by_ids: dict,
    organisation: Organisation,
    website: Website,
    sample: bool,
) -> dict:
    logger.info(f"Filtering by risk score, current count {len(light_post_by_ids)}")

    try:
        posts_to_skip_by_ids = {}
        posts_to_filter_by_ids = {}
        for post_id, light_post in light_post_by_ids.items():
            if light_post.get("title") is None and light_post.get("description") is None:
                posts_to_skip_by_ids[post_id] = light_post
            else:
                posts_to_filter_by_ids[post_id] = light_post

        posts_to_scrape_by_ids = filter_by_risk_score(
            posts_to_filter_by_ids,
            filtering_threshold=get_filtering_threshold(organisation),
            organisation_name=organisation.name,
            domain_name=website.domain_name,
            sample=sample,
        )

        posts_to_scrape_by_ids.update(posts_to_skip_by_ids)

        for post_id in light_post_by_ids:
            post_DAO.update_post_filter_status(
                platform_id=post_id,
                organisation_id=organisation.id,
                website_id=website.id,
                status=(
                    ScrapingStatus.FILTERED_IN if post_id in posts_to_scrape_by_ids else ScrapingStatus.FILTERED_OUT
                ),
            )
    except Exception as e:
        logger.error(f"Error filtering marketplace search results by risk score: {repr(e)}")
        sentry_sdk.capture_exception(e)
        posts_to_scrape_by_ids = light_post_by_ids

    logger.info(
        f"Filtering marketplace search results by risk score completed. new count {len(posts_to_scrape_by_ids)}"
    )

    return posts_to_scrape_by_ids


def filter_by_risk_score(
    light_post_by_ids: dict,
    filtering_threshold: Optional[float],
    organisation_name: str,
    domain_name: str,
    sample: bool,
) -> dict:
    logger.info("Computing risk score for posts")

    if not light_post_by_ids:
        return {}

    light_posts = convert_to_light_posts(
        light_post_by_ids, organisation_name=organisation_name, domain_name=domain_name
    )

    prediction_by_post_ids = predict_risk_score(light_posts, organisation_name=organisation_name)

    posts_to_scrape_by_ids = {}
    for post_id in light_post_by_ids:
        risk_score = prediction_by_post_ids.get(post_id) and prediction_by_post_ids[post_id]["Label_predicted"]
        light_post_by_ids[post_id]["risk_score"] = risk_score

        post_DAO.add_filter_logs(
            light_post_log_id=light_post_by_ids[post_id]["light_post_log_id"],
            filter_post_payload=prediction_by_post_ids.get(post_id),
            risk_score=risk_score,
        )

        if not filtering_threshold or not risk_score or risk_score > filtering_threshold:
            posts_to_scrape_by_ids[post_id] = light_post_by_ids[post_id]

    logger.info(
        f"Found {len(posts_to_scrape_by_ids)} posts above threshold {filtering_threshold} for website {domain_name} & organisation {organisation_name} ({len(posts_to_scrape_by_ids)/len(light_post_by_ids)*100:.2f}% of total)"
    )

    # Random sampling
    if not sample:
        return posts_to_scrape_by_ids

    for post_id in light_post_by_ids.keys():
        if random.random() > FILTERING_RATE:
            continue

        logger.info(
            f"Skip filtering for post {post_id} with risk_score {light_post_by_ids[post_id]['risk_score']} for website {domain_name} & organisation {organisation_name}"
        )

        posts_to_scrape_by_ids[post_id] = light_post_by_ids[post_id]
        posts_to_scrape_by_ids[post_id]["tags"].append("unfiltered")
        posts_to_scrape_by_ids[post_id]["skip_filter_scraped_results"] = True

    return posts_to_scrape_by_ids


def convert_to_light_posts(light_post_by_ids: dict, organisation_name: str, domain_name: str) -> List[BasePost]:
    light_posts: List[BasePost] = []
    for post_id, light_post in light_post_by_ids.items():
        if not light_post:
            continue

        light_posts.append(
            BasePost(
                id=post_id,
                url=light_post["url"],
                organisation=BaseOrganisation(
                    name=organisation_name,
                ),
                title=light_post.get("title", ""),
                description=light_post.get("description", ""),
                images=[
                    BaseImage(
                        url=image_url if type(image_url) == str else image_url["picture_url"],
                        s3_url=None if type(image_url) == str else image_url["s3_url"],
                    )
                    for image_url in light_post["pictures"]
                ],
                website=BaseWebsite(domain_name=domain_name, website_category="Marketplace"),
            )
        )

    logo_predictions = get_logo_prediction(light_posts)
    translate_posts(light_posts)

    for post in light_posts:
        for image in post.images:
            image_url = image.s3_url or image.url
            image.logo_predictions = logo_predictions[image_url] if image_url in logo_predictions else None
            image.logo_detected = (
                organisation_name in logo_predictions[image_url] if image_url in logo_predictions else None
            )

    return light_posts


def predict_risk_score(light_posts: List[BasePost], organisation_name: str) -> dict:
    model_name_by_organisation = {
        "Zagtoon": "zag_v1",
    }

    return prefiltering_predictions(
        posts=light_posts, model_name=model_name_by_organisation.get(organisation_name, "marketplaces_v3.1.1")
    )
