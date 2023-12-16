import os

from automated_moderation.post_getter.from_db import LightPostGetter, DBPostGetter
from automated_moderation.feature.feature_registry import FEATURE_REGISTRY
from automated_moderation.feature import EnumeratedFeatureSet
from automated_moderation.model import TrainingRunner
from automated_moderation.dataset.dataset import Dataset

DF_FOLDER = "automated_moderation/models/dataframe/"
TEST_SAMPLE_SIZE = 100


def get_datasets():
    test_datasets, train_datasets = [], []

    marketplace_test_dataset = Dataset(
        tag="marketplace_training_data_pt_1", date="2023-03-20", post_getter=LightPostGetter()
    )
    marketplace_test_dataset.extend()
    test_datasets.append(marketplace_test_dataset)

    # gucci_test_dataset = Dataset(
    #     tag="automated_moderation_ig_10_05", date="2023-03-20", post_getter=DBPostGetter(one_image=True)
    # )
    # gucci_test_dataset.reduce(TEST_SAMPLE_SIZE)
    # test_datasets.append(gucci_test_dataset)

    ig_small_brands_dataset = [
        Dataset(
            tag="automated_moderation_ig_sergio_rossi_extract",
            date="2023-03-27",
            post_getter=DBPostGetter(one_image=True),
            weight=10,
        ),
        Dataset(
            tag="automated_moderation_ig_rimowa_extract",
            date="2023-03-27",
            post_getter=DBPostGetter(one_image=True),
            weight=10,
        ),
        Dataset(
            tag="automated_moderation_ig_hublot_extract",
            date="2023-03-27",
            post_getter=DBPostGetter(one_image=True),
            weight=10,
        ),
    ]
    for dataset in ig_small_brands_dataset:
        train_dataset, test_dataset = dataset.split(test_sample_size=TEST_SAMPLE_SIZE)
        train_datasets.append(train_dataset)
        test_datasets.append(test_dataset)

    test_dataset = Dataset.merge(test_datasets)

    for df_name in os.listdir(DF_FOLDER):
        df_infos = df_name.split("__")
        if len(df_infos) < 2:
            continue

        date = df_infos[0]
        domain_name = (
            df_infos[1].split(":")[1].replace(".parquet", "").replace("_", ".")
            if "domain_name" in df_infos[1]
            else None
        )

        if domain_name is None:
            continue

        dataset = Dataset(domain_name=domain_name, date=date, post_getter=LightPostGetter())

        if domain_name == "instagram.com":
            # Keep only posts from big brands
            ig_big_brands = ["Gucci", "Chanel_Navee", "LouisVuitton", "Dior", "Celine"]
            dataset.posts = dataset.posts[dataset.posts["organisation.name"].isin(ig_big_brands)]

            # Create a test dataset for each big brand except Gucci (already done)
            dataset, test_dataset = dataset.split(test_sample_size=TEST_SAMPLE_SIZE)
            test_dataset.posts = test_dataset.posts[test_dataset.posts["organisation.name"] != "Gucci"]
            test_datasets.append(test_dataset)

        # Remove posts that are already in the test dataset
        dataset.remove(test_dataset.posts["id"].values)

        dataset.extend()
        train_datasets.append(dataset)

    train_dataset = Dataset.merge(train_datasets)

    return train_dataset, test_dataset


def main():
    train_dataset, test_dataset = get_datasets()

    model_runner = TrainingRunner(
        feature_set=EnumeratedFeatureSet(
            FEATURE_REGISTRY.get_slice(
                include_tags={"tg_all"},
                exclude_tags={
                    "tg_need_post_scraping",
                    "tg_need_history",
                    "tg_need_classification",
                    "tg_instagram",
                },
            )
        ),
    )

    model_runner.train(dataset=train_dataset)
    model_runner.test(dataset=test_dataset)
    model_runner.analyse_model()


if __name__ == "__main__":
    main()
