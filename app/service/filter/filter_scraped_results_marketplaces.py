from typing import Optional

from app.dao import OrganisationDAO
from app.service.filter.utils import (
    filter_by_exclude_keywords,
    filter_by_must_have_keywords,
    dispatch_among_organisations,
)
from app.models import Organisation

MARKETPLACE_FILTERING_ORG = []

organisation_DAO = OrganisationDAO()


def filter_marketplace_scraped_results(scraped_posts: list, organisation: Optional[Organisation]):
    if not organisation:
        return dispatch_among_organisations(scraped_posts)

    if organisation.exclude_keywords:
        scraped_posts = filter_by_exclude_keywords(
            posts=scraped_posts,
            exclude_keywords=organisation.exclude_keywords.split(","),
        )

    if organisation.must_have_keywords:
        scraped_posts = filter_by_must_have_keywords(
            posts=scraped_posts,
            must_have_keywords=organisation.must_have_keywords.split(","),
        )

    return scraped_posts
