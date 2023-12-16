from dataclasses import dataclass, asdict, field
from datetime import datetime
import os
import pandas as pd
from typing import List, Optional

from .dataset import Dataset
from automated_moderation.post_getter.from_db import LightPostGetter
from automated_moderation.utils.logger import log


@dataclass
class LightPostsDataset(Dataset):
    organisations: List[str] = field(default_factory=list)
    organisation: Optional[str] = None
    tag: Optional[str] = None
    balance: bool = True

    def __post_init__(self):
        if self.organisation:
            self.organisations = [self.organisation]

        self.date = self.date or datetime.now().strftime("%Y-%m-%d")
        self.name = self.get_name()
        self.path = self.folder_path / f"{self.name}.parquet"

        self.load_all_posts()

    def get_name(self) -> str:
        name = f"{self.date}__light_posts_dataset"

        if self.tag:
            name += f"__tag:{self.tag}"

        if self.organisation:
            name += f"__organisation:{self.organisation}"

        return name

    def load_all_posts(self) -> pd.DataFrame:
        pool_names = [
            pool_name for pool_name in os.listdir(Dataset.folder_path) if "__light_posts_dataset" in pool_name
        ]

        if self.tag:
            pool_names = [pool_name for pool_name in pool_names if f"__tag:{self.tag}" in pool_name]
        else:
            pool_names = [pool_name for pool_name in pool_names if "__tag:" not in pool_name]

        if self.organisation:
            pool_names = [pool_name for pool_name in pool_names if f"__organisation:{self.organisation}" in pool_name]
        else:
            pool_names = [pool_name for pool_name in pool_names if "__organisation:" not in pool_name]

        if not pool_names:
            self.create()
        else:
            last_pool = sorted(pool_names, reverse=True)[0]
            self.last_update_date = last_pool.split("__")[0] if pool_names else "2023-01-01"
            self.posts = pd.read_parquet(Dataset.folder_path / last_pool)

        self.posts["weight"] = self.weight or 1

    def create(self):
        log.info("Creating dataset from scratch")
        self.posts = pd.DataFrame()
        for organisation in self.organisations:
            post_getter = LightPostGetter(begin_date="2023-01-01", balance=self.balance)
            new_posts = post_getter.get(organisation_name=organisation, tag=self.tag)

            new_posts = pd.json_normalize(asdict(post) for post in new_posts)
            self.posts = pd.concat([self.posts, new_posts])
            self.save(self.posts)

    def update(self):
        log.info(f"Updating dataset since {self.last_update_date}")
        for organisation in self.organisations:
            post_getter = LightPostGetter(begin_date=self.last_update_date)
            new_posts = post_getter.get(organisation_name=organisation)

            new_posts = pd.json_normalize(asdict(post) for post in new_posts)
            self.posts = pd.concat([self.posts, new_posts])

            self.save(self.posts)

    def balance_with_weights_as(self, test_dataset: pd.DataFrame):
        organisations = self.posts["organisation.name"].unique()
        ideal_posts_nb_per_org = len(self.posts) / len(organisations)
        for organisation in organisations:
            organisation_weight = ideal_posts_nb_per_org / len(
                self.posts[self.posts["organisation.name"] == organisation]
            )

            test_posts_nb_by_label = (
                test_dataset[test_dataset["organisation.name"] == organisation]["label_name"].value_counts().to_dict()
            )
            test_posts_nb = len(test_dataset[test_dataset["organisation.name"] == organisation])

            train_posts_nb_by_label = (
                self.posts[self.posts["organisation.name"] == organisation]["label_name"].value_counts().to_dict()
            )
            train_posts_nb = len(self.posts[self.posts["organisation.name"] == organisation])

            for label in test_posts_nb_by_label:
                self.posts.iloc[
                    (self.posts["organisation.name"] == organisation) & (self.posts["label_name"] == label),
                    self.posts.columns.get_loc("weight"),
                ] = (
                    organisation_weight
                    * (test_posts_nb_by_label[label] / test_posts_nb * train_posts_nb)
                    / train_posts_nb_by_label[label]
                )
