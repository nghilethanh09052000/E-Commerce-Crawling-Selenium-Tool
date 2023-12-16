from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import os
from copy import deepcopy

import pandas as pd
from sklearn.model_selection import train_test_split

from automated_moderation.post_getter import PostGetter
from automated_moderation.utils.logger import log
from automated_moderation.utils.config import LABEL_TO_PREDICTION


MIN_POSTS = 10


@dataclass
class Dataset:
    folder_path = Path("automated_moderation/models/dataframe")

    domain_name: Optional[str] = None
    tag: Optional[str] = None
    organisation_name: Optional[str] = None
    reload: bool = False
    load_all: bool = False
    post_getter: Optional[PostGetter] = None
    date: Optional[str] = None
    posts: pd.DataFrame = None
    weight: Optional[float] = None

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d")

        self.name = self.get_name()
        self.path = self.folder_path / f"{self.name}.parquet"

        if self.posts is None:
            self.posts = self.load_posts_with_save(self.path) if not self.load_all else self.load_all_posts()

        if self.weight:
            self.posts["weight"] = self.weight

    def get_name(self):
        name = str(self.date)
        if self.organisation_name:
            name += f"__organisation_name:{self.organisation_name}"
        if self.domain_name:
            name += f'__domain_name:{self.domain_name.replace(".", "_")}'
        if self.tag:
            name += f"__tag:{self.tag}"

        return name

    def reduce(self, max_posts: int, random_state: int = 200):
        self.posts = self.posts.sample(frac=1, random_state=random_state)  # shuffle
        self.posts = self.posts[:max_posts]

    def save(self, posts: pd.DataFrame):
        posts.to_parquet(self.path)

    def load_posts_with_save(self, path: Path) -> pd.DataFrame:
        if path.exists() and not self.reload:
            log.info(f"Loading posts from save at {path}...")
            return pd.read_parquet(path)

        return self.load_posts()

    def load_all_posts(self):
        pool_names = [
            pool_name
            for pool_name in os.listdir(Dataset.folder_path)
            if not self.domain_name or self.domain_name.replace(".", "_") in pool_name
        ]
        posts = pd.DataFrame()
        for pool_name in pool_names:
            organisation_name = pool_name.split("__")[0]
            new_posts = self.load_posts_with_save(path=(Dataset.folder_path / pool_name))
            new_posts["id"] = organisation_name + ":" + new_posts["id"].astype(str)

            posts = pd.concat([posts, new_posts])

        return posts

    def load_posts(self) -> pd.DataFrame:
        posts = self.post_getter.get(
            organisation_name=self.organisation_name, domain_name=self.domain_name, tag=self.tag
        )

        posts = pd.json_normalize(asdict(post) for post in posts)
        self.save(posts)

        return posts

    def extend(self, organisation_names: List[str] = [], label_to_prediction: Dict = LABEL_TO_PREDICTION):
        log.info(f"Extending pool {self.name}...")

        # if an organisation has less than MIN_POSTS posts for a domain, remove the posts from the pool
        for organisation_name in self.posts["organisation.name"].unique():
            for domain_name in self.posts["website.domain_name"].unique():
                organisation_posts = self.posts[
                    (self.posts["organisation.name"] == organisation_name)
                    & (self.posts["website.domain_name"] == domain_name)
                ]
                if len(organisation_posts) < MIN_POSTS:
                    self.posts = self.posts[
                        (self.posts["organisation.name"] != organisation_name)
                        | (self.posts["website.domain_name"] != domain_name)
                    ]

        # Keep organisations with more than MIN_POSTS posts
        valid_orgs = (
            self.posts["organisation.name"]
            .value_counts()
            .reset_index(name="count")
            .query("count >= @MIN_POSTS")["index"]
            .to_list()
        )
        organisation_names = [o for o in organisation_names if o in valid_orgs] if organisation_names else valid_orgs

        base_posts = self.posts.copy(deep=True)
        self.posts = pd.DataFrame()
        for organisation_name in organisation_names:
            posts = base_posts.copy(deep=True)
            posts = posts[
                (posts["organisation.name"] == organisation_name)
                | (posts["label_name"].apply(lambda x: label_to_prediction[x]) == 1)
            ]
            self.link_post_to_org(posts=posts, organisation_name=organisation_name)
            self.posts = pd.concat([self.posts, posts])

    def link_post_to_org(self, posts: pd.DataFrame, organisation_name: str):
        posts["label_name"] = posts.apply(self.link_post_label_to_org, args=(organisation_name,), axis=1)
        posts["organisation.name"] = organisation_name
        posts["images"] = posts["images"].apply(self.link_post_images_to_org, args=(organisation_name,))

    def link_post_label_to_org(self, post: pd.Series, organisation_name: str):
        if post["organisation.name"] != organisation_name:
            return "Irrelevant"
        return post["label_name"]

    def link_post_images_to_org(self, post_images: pd.Series, organisation_name: str):
        images = deepcopy(post_images)
        for image in images:
            image["logo_detected"] = (
                bool(organisation_name in image["logo_predictions"]) if image["logo_predictions"] is not None else None
            )

        return images

    def split(
        self,
        frac: float = 0.8,
        random_state: int = 200,
        test_sample_size: Optional[int] = None,
        stratify_by: Optional[str] = "organisation.name",
    ) -> Tuple["Dataset", "Dataset"]:
        if test_sample_size:
            frac = 1 - (test_sample_size / len(self.posts))

        log.info(f"Splitting dataset with frac={frac}...")

        posts_1, posts_2 = train_test_split(
            self.posts,
            train_size=frac,
            random_state=random_state,
            stratify=self.posts[stratify_by] if stratify_by else None,
        )

        return Dataset(posts=posts_1, domain_name=self.domain_name), Dataset(
            posts=posts_2, domain_name=self.domain_name
        )

    @classmethod
    def merge(cls, datasets: List["Dataset"], random_state: int = 200) -> "Dataset":
        posts = pd.concat([dataset.posts for dataset in datasets])
        posts = posts.sample(frac=1, random_state=random_state)  # shuffle
        return cls(posts=posts)

    def remove(self, ids: List[str]):
        self.posts = self.posts[~self.posts["id"].isin(ids)]
