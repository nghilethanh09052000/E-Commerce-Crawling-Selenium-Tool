from automated_moderation.feature.feature_registry import FEATURE_REGISTRY
from automated_moderation.feature import EnumeratedFeatureSet
from automated_moderation.model import TrainingRunner
from automated_moderation.dataset.light_posts import LightPostsDataset

SUPPORTED_ORGANISATIONS = [
    "Zagtoon",
]

LABEL_TO_PREDICTION = {
    "Counterfeit": 1,
    "Infringement": 1,
    "Irrelevant": 0,
    "Legitimate": 1,
    "Phishing": 1,
    "Suspicious": 1,
}


def main():
    train_dataset = LightPostsDataset(organisation="Zagtoon")
    # train_dataset.update()

    test_dataset = LightPostsDataset(organisation="Zagtoon", tag="unfiltered_sample", balance=False)
    # test_dataset.update()
    train_dataset.remove(ids=test_dataset.posts["id"].tolist())

    model_runner = TrainingRunner(
        feature_set=EnumeratedFeatureSet(
            FEATURE_REGISTRY.get_slice(
                include_tags={"tg_all"},
                exclude_tags={
                    "tg_need_post_scraping",
                    "tg_need_history",
                    "tg_need_classification",
                    "tg_instagram",
                    "f_text_post__text_without_organisation",
                },
            )
        ),
        label_to_prediction=LABEL_TO_PREDICTION,
    )

    model_runner.train(dataset=train_dataset)
    model_runner.test(dataset=test_dataset)
    model_runner.analyse_model()


if __name__ == "__main__":
    main()
