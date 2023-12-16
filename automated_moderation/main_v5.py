from automated_moderation.post_getter.from_db import LightPostGetter
from automated_moderation.feature.feature_registry import FEATURE_REGISTRY
from automated_moderation.feature import EnumeratedFeatureSet
from automated_moderation.model import TrainingRunner
from automated_moderation.dataset import Dataset

def build_pool(reload: bool = False):
    Dataset(tag="marketplace_training_data_pt_1", date="2023-03-20", post_getter=LightPostGetter(), reload=reload)


def main():
    shopee_dataset = Dataset(domain_name="shopee.tw", date="2023-03-07")
    shopee_dataset.extend()

    test_dataset = Dataset(tag="marketplace_training_data_pt_1", date="2023-03-20", post_getter=LightPostGetter())
    test_dataset.extend()

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

    model_runner.train(dataset=shopee_dataset)
    model_runner.test(dataset=test_dataset)
    model_runner.analyse_model()

if __name__ == "__main__":
    main()