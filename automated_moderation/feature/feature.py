from enum import Enum
from typing import Set, List, Union
import re

import pandas as pd

from automated_moderation.dataset import BasePost


class Feature:
    # e.g. "f_num_post__images_count"
    NAME_REGEX = r"^(f_[a-zA-Z]+)_(\w+)__(\w+)$"

    class FType(str, Enum):
        NUM = "f_num"
        CAT = "f_cat"
        TEXT = "f_text"
        ID = "f_id"
        AUX = "f_aux"
        LABEL = "f_label"

    # Having the object type right in the name of the feature is useful because it prevents name collisions when doing joins of linked data, e.g. [image X post X accound X vendor].
    # This can be seen as a namespace. We have it in the name because ML models typically don't support namespaces and use flat list of unique feature names.
    # Whenever possible stick to names from app/models to avoid confusion.
    class AttributeOf(str, Enum):
        # features that depend only on the current post (e.g. "title of the post has keyword X") or post-wise arggregates of linked objects (e.g. "some images of this post has logo")
        POST = "post"

        # features that depend only on the current organisation (if it's fixed), e.g. "organisation name" or "this organisation produces handbags"
        ORGANISATION = "organisation"

        # features that depend on a combination of post and organisation, e.g. "the description of the current post mentions the current organisation" (not "some organisation", this organisation)
        POST_ORGANISATION = "post_organisation"

        ACCOUNT = "account"
        ACCOUNT_ORGANISATION = "account_organisation"

        CLUSTER = "cluster"
        CLUSTER_ORGANISATION = "cluster_organisation"

        IMAGE = "image"
        DUPLICATED_GROUP = "duplicated_group"

        WEBSITE = "website"

    TAGS = (
        {
            "tg_all",  # select all features for debugging purposes
            #
            #
            # Life-cycle
            "tg_unimplemented",  # "work in progress", can't calculate this feature yet
            "tg_implemented",  # feature is implemented and but is not used in production yet
            "tg_public",  # feature used in a production model; don't modify it, create a new _v2 feature if necessary and deprecate the old one
            "tg_deprecated",  # feature still supported and probably used in production, but should be excluded from the training of new models
            "tg_removed",  # deleted feature, not used by any active models, no code to calculate it; basically a placeholder to avoid re-use of the name
            #
            #
            # What data is needed to calculate the feature.
            # Can be used to select features available at specific parts of the pipeline. E.g. you want to do pre-insertion filtering, most of the DB fields are not available at that point
            "tg_need_search_results",
            "tg_need_post_scraping",
            "tg_need_first_image",
            "tg_need_history",
            "tg_need_classification",
            "tg_need_translation",
            "tg_need_vit",
            "tg_instagram",
            #
            #
            # How feature is calculated
            # Typically you have a function that calculates a bunch of closely related features. You create a tag that matches this function and select all these featers at once.
            "tg_post_basic",  # simple features that can be directly derived from the object fields in the database, e.g. "numer of images in the post"
        }
        .union(set(("tg_") + t.value for t in FType))
        .union(set(("tg_") + t.value for t in AttributeOf))
    )

    def __init__(self, name: str, description: str = "", default_value: Union[str, int] = -1, tags: Set[str] = set()):
        self.name = name
        self.description = description
        self.default_value = default_value

        # special case
        if name == "f_label":
            self.ftype = "f_label"
            return

        m = re.match(Feature.NAME_REGEX, self.name)
        if not m:
            raise ValueError(f"Bad feature name: '{name}', expected format '{Feature.NAME_REGEX}'")

        self.ftype = Feature.FType(m.group(1))
        self.attribute_of = Feature.AttributeOf(m.group(2))
        self.suffix = m.group(3)

        # add synthetic tags
        tags.update({"tg_all", "tg_" + self.ftype, "tg_" + self.attribute_of})
        unknown_tags = tags.difference(self.TAGS)
        if len(unknown_tags) > 0:
            raise (ValueError(f"Unknown tags: {unknown_tags}"))

        tags.update({self.name})
        self.tags = tags

    def is_good_for_tags(self, include_tags: Set[str], exclude_tags: Set[str]):
        # has at least one "include tag"
        # has none of the "exclude tags"
        return len(self.tags.intersection(include_tags)) > 0 and len(self.tags.intersection(exclude_tags)) == 0

    def get_post_data(self, posts: List[BasePost]) -> pd.DataFrame:
        res = []
        for post in posts:
            res.append([post.id, self.post_to_feature(post)])
        return pd.DataFrame(res, columns=["id", self.name])

    def df_to_feature(self, posts: pd.DataFrame):
        raise NotImplementedError()

    def post_to_feature(self, post: BasePost):
        raise NotImplementedError()
