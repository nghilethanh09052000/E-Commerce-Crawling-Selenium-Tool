from automated_moderation.dataset.dataset_feature import IsDescCounterfeitFeatureDataset
from automated_moderation.dataset import BasePost
from automated_moderation.model import TrainingRunner
from automated_moderation.feature.feature_registry import PostTranslatedText
from automated_moderation.feature import EnumeratedFeatureSet


if __name__ == "__main__":
    dataset = IsDescCounterfeitFeatureDataset(PostType=BasePost, name="is_desc_counterfeit_121222")
    train_dataset, test_dataset = dataset.split()

    features = [PostTranslatedText()]
    model_runner = TrainingRunner(
        model_name="is_desc_counterfeit_v1",
        feature_set=EnumeratedFeatureSet(features={f.name: f for f in features}),
    )

    model_runner.train(dataset=train_dataset)
    model_runner.test(dataset=test_dataset)
    model_runner.analyse_model()
