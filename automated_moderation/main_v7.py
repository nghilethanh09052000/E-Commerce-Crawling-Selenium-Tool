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
    train_dataset = LightPostsDataset(organisations=SUPPORTED_ORGANISATIONS)
    train_dataset.update()

    test_dataset = LightPostsDataset(organisations=SUPPORTED_ORGANISATIONS, tag="unfiltered_sample", balance=False)
    test_dataset.update()

    train_dataset.balance_with_weights_as(test_dataset.posts)

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
                    "tg_unimplemented",
                    "tg_need_vit",
                },
            )
        ),
        depth=8,
        # iterations = 10000,
        # learning_rate = 0.01,
        # od_type = 'Iter',
        # od_wait = 100,
        # use_best_model = True,
        # grid = {
        #     'depth':[6,8,10],
        #     'iterations':[5000],
        #     'learning_rate': [0.03,0.05,0.08],
        #     'od_type':['Iter'],
        #     'od_wait':[30],
        #     'l2_leaf_reg':[1,3,5,10],
        #     'bagging_temperature':[0,0.3,0.5,1],
        #     'grow_policy':['SymmetricTree', 'Depthwise', 'Lossguide'],
        # },
        # use_params_search = True,
    )

    model_runner.train(dataset=train_dataset)
    model_runner.test(dataset=test_dataset)
    model_runner.analyse_model()


if __name__ == "__main__":
    main()
