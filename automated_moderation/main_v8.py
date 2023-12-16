from automated_moderation.feature.feature_registry import FEATURE_REGISTRY
from automated_moderation.feature import EnumeratedFeatureSet
from automated_moderation.model import TrainingRunner
from automated_moderation.dataset.light_posts import LightPostsDataset

SUPPORTED_ORGANISATIONS = [
    "Fred",
    "Brunello_Cucinelli",
    "Chanel_Navee",
    "Sony_Entertainment",
    "Kenzo",
    "Gucci",
    "Vibram",
    "Rimowa",
    "Dior",
    "Celine",
    "Hublot",
    "Sergio_Rossi",
    # "Zagtoon",
    "Louis_Vuitton",
]


def main():
    unfiltered_sample_dataset = LightPostsDataset(organisations=SUPPORTED_ORGANISATIONS, tag="unfiltered_sample")
    train_dataset, test_dataset = unfiltered_sample_dataset.split(frac=0.2, stratify_by=None)

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
