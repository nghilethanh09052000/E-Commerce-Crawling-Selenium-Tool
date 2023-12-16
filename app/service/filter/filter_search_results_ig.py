from typing import List, Dict, Optional
import random
from copy import deepcopy
from dataclasses import asdict

from rich.progress import track

from automated_moderation.dataset import BasePost, BaseOrganisation
from app import logger
from app.helpers.utils import load_instagram_search_configs
from app.service.filter.utils import prefiltering_predictions
from app.helpers.translation import translate_posts
from app.api.logo_detection import get_logo_prediction
from app.models import Organisation
from app.service.filter.utils import filter_by_exclude_keywords, FILTERING_RATE
from app.settings import sentry_sdk


def filter_ig_search_results(
    light_posts: List[BasePost], organisation: Optional[Organisation], sample: bool
) -> Dict[str, BasePost]:
    if organisation and organisation.exclude_keywords:
        post_to_scrape = filter_by_exclude_keywords(
            posts=[asdict(post) for post in light_posts],
            exclude_keywords=organisation.exclude_keywords.split(","),
        )
        post_ids_to_scrape = [post["id"] for post in post_to_scrape]
        light_posts = [post for post in light_posts if post.id in post_ids_to_scrape]

    posts_to_scrape = filter_by_risk_score_safe(
        light_posts=light_posts,
        filtering_threshold=(0.5 if not organisation or organisation.activate_filtering else None),
        organisation=organisation,
        sample=sample,
    )

    return posts_to_scrape


def filter_by_risk_score_safe(
    light_posts: List[BasePost],
    filtering_threshold: Optional[float],
    organisation: Optional[Organisation],
    sample: bool,
) -> Dict[str, BasePost]:
    logger.info(f"Filtering by risk score, current count {len(light_posts)}")

    logo_predictions = get_logo_prediction(light_posts)
    translate_posts(light_posts)

    posts_to_scrape = filter_by_risk_score(
        light_posts=light_posts,
        logo_predictions=logo_predictions,
        filtering_threshold=filtering_threshold,
        organisation_name=organisation.name if organisation else None,
        sample=sample,
    )

    logger.info(f"Filtering ig search results by risk score completed. new count {len(posts_to_scrape)}")

    return posts_to_scrape


def filter_by_risk_score(
    light_posts: List[BasePost],
    logo_predictions: Dict,
    filtering_threshold: Optional[float],
    organisation_name: Optional[str],
    sample: bool,
) -> Dict[str, BasePost]:
    for post in light_posts:
        for image in post.images:
            image_url = image.s3_url or image.url
            image.logo_predictions = logo_predictions[image_url] if image_url in logo_predictions else None

    ig_organisations = list(load_instagram_search_configs().keys())
    ig_organisations.remove("Commons")

    all_posts = {post.id: post for post in deepcopy(light_posts)}
    valid_posts: Dict[str, BasePost] = {}
    for ig_organisation in track(ig_organisations):
        # Prepare post
        for post in light_posts:
            post.organisation = BaseOrganisation(name=ig_organisation)
            for image in post.images:
                image.logo_detected = (
                    ig_organisation in logo_predictions[image.url] if image.url in logo_predictions else None
                )

        # Get predictions
        post_to_prefiltering_score = prefiltering_predictions(posts=light_posts, model_name="ig_6_brands_v1")
        for post_id, post in post_to_prefiltering_score.items():
            all_posts[post_id].risk_score[ig_organisation] = post["Label_predicted"]

        # Clear light posts parameters
        for post in light_posts:
            post.organisation = None
            for image in post.images:
                image.logo_detected = None

    # Set organisation we scraped the posts for
    for post in light_posts:
        post.organisation = BaseOrganisation(name=organisation_name)

    # Get posts above threshold
    for id, post in all_posts.items():
        if not post.risk_score:
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("post", post)
                scope.set_extra("id", id)
                sentry_sdk.capture_message("Risk score prediction failed")

            continue

        risk_score = max(post.risk_score.values())

        if filtering_threshold is None or risk_score > filtering_threshold:
            valid_posts[id] = post

    logger.info(
        f"Found {len(valid_posts)} posts above threshold {filtering_threshold} for website instagram.com & organisation {organisation_name}"
    )

    if not sample or not filtering_threshold:
        return valid_posts

    # Random sampling
    for post_id in all_posts.keys():
        if random.random() > FILTERING_RATE:
            continue

        org = organisation_name or random.choice(ig_organisations)

        logger.info(
            f"Skip filtering for post {post_id} with risk_score {all_posts[post_id].risk_score[org]} for website instagram.com & organisation {org}"
        )

        valid_posts[post_id] = all_posts[post_id]
        valid_posts[post_id].tags.append("unfiltered")
        valid_posts[post_id].skip_filter_scraped_results = True
        valid_posts[post_id].valid_organisations.append(org)

    return valid_posts
