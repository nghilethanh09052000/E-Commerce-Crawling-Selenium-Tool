from automated_moderation.model import PredictionRunner
from automated_moderation.feature.feature_registry import FEATURE_REGISTRY

from automated_moderation.dataset.light_posts import LightPostsDataset

from automated_moderation.utils.config import LABEL_TO_PREDICTION


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

if __name__ == "__main__":
    runner = PredictionRunner(model_name="marketplaces_v3.1.1", feature_registry=FEATURE_REGISTRY)
    test_dataset = LightPostsDataset(organisations=SUPPORTED_ORGANISATIONS, tag="unfiltered_sample", balance=False)
    test_dataset.posts["Label"] = test_dataset.posts["label_name"].apply(lambda x: LABEL_TO_PREDICTION[x])
    runner.predict(test_dataset.posts)
    runner.analyse_model()
