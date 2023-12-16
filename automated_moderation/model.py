import time
from pathlib import Path
from typing import Dict

from catboost import Pool, CatBoostRegressor
import pandas as pd
from sklearn.metrics import precision_recall_curve
import matplotlib.pyplot as plt
import numpy as np

from automated_moderation.feature import EnumeratedFeatureSet, FeatureRegistry
from automated_moderation.dataset.dataset import Dataset
from automated_moderation.utils.logger import log
from automated_moderation.utils.config import LABEL_TO_PREDICTION


MODELS_PATH = Path("automated_moderation/models")


class Model:
    def __init__(
        self,
        model_name: str = None,
        path: Path = None,
        feature_set: EnumeratedFeatureSet = None,
        feature_registry: FeatureRegistry = None,
        depth=None,
        iterations=None,
        learning_rate=None,
        od_type=None,
        od_wait=None,
        use_best_model=False,
        grid=None,
        use_params_search=False,
    ) -> None:
        if use_params_search and grid:
            self.regressor = CatBoostRegressor(
                one_hot_max_size=100,
            )
            self.grid = grid
        else:
            self.regressor = CatBoostRegressor(
                one_hot_max_size=100,
                depth=depth,
                iterations=iterations,
                learning_rate=learning_rate,
                od_type=od_type,
                od_wait=od_wait,
                use_best_model=use_best_model,
            )
            self.grid = None

        self.model_name = model_name
        self.path = path

        self.model_path = path / "model"
        self.columns_description_path = self.path / "columns_description.cd"

        if feature_set:
            self.set_features_set(feature_set)
            self.feature_set.create_columns_description(self.columns_description_path)
        elif feature_registry:
            self.load_model(path=path, feature_registry=feature_registry)
        else:
            raise RuntimeError("feature_set or feature_registry should be specified")

    def load_model(self, path: Path, feature_registry: FeatureRegistry):
        self.regressor.load_model(fname=(path / "model"))
        self.set_features_set(
            feature_set=EnumeratedFeatureSet(
                load_from_path=(path / "columns_description.cd"), feature_registry=feature_registry
            )
        )

    def set_features_set(self, feature_set: EnumeratedFeatureSet):
        self.feature_set = feature_set
        self.feature_names = self.feature_set.get_feature_names()
        self.cat_features = [f for f in self.feature_names if f.startswith("f_cat")]
        self.text_features = [f for f in self.feature_names if f.startswith("f_text")]

    def compute_features(self, posts: pd.DataFrame):
        self.feature_set.to_df(posts)

    def predict(self, df: pd.DataFrame):
        df = df[[f.name for f in self.feature_set.features_dict.values()]]
        prediction_pool = Pool(
            data=df,
            cat_features=self.cat_features,
            text_features=self.text_features,
            feature_names=self.feature_names,
        )

        return self.regressor.predict(prediction_pool)

    def train(self, df: pd.DataFrame, val_df: pd.DataFrame):
        df = df[[f.name for f in self.feature_set.features_dict.values()] + ["Label", "weight"]]
        val_df = val_df[[f.name for f in self.feature_set.features_dict.values()] + ["Label", "weight"]]
        train_pool = Pool(
            data=df.drop(["Label", "weight"], axis=1, errors="ignore"),
            cat_features=self.cat_features,
            text_features=self.text_features,
            feature_names=self.feature_names,
            label=df[["Label"]],
            weight=df[["weight"]],
        )
        val_pool = Pool(
            data=val_df.drop(["Label", "weight"], axis=1, errors="ignore"),
            cat_features=self.cat_features,
            text_features=self.text_features,
            feature_names=self.feature_names,
            label=val_df[["Label"]],
            weight=val_df[["weight"]],
        )

        self.regressor.fit(train_pool, eval_set=val_pool)
        self.regressor.save_model(self.model_path, pool=train_pool)

    def params_search(self, df: pd.DataFrame):
        df = df[[f.name for f in self.feature_set.features_dict.values()] + ["Label", "weight"]]
        train_pool = Pool(
            data=df.drop(["Label", "weight"], axis=1, errors="ignore"),
            cat_features=self.cat_features,
            text_features=self.text_features,
            feature_names=self.feature_names,
            label=df[["Label"]],
            weight=df[["weight"]],
        )

        self.regressor.randomized_search(self.grid, train_pool)
        self.regressor.save_model(self.model_path, pool=train_pool)

    def feature_analysis(self):
        if self.text_features or self.cat_features:
            print("Features analysis not supported for text & categorical features")
            return

        self.regressor.calc_feature_statistics(
            data=self.train_df.drop(["Label", "id"], axis=1),
            target=self.train_df[["Label"]],
            feature=self.feature_names,
            plot_file=str(self.path / "feature_analysis.html"),
            plot=False,
        )

        print(f"\nSaved feature analysis at automated_moderation/models/{self.model_name}/feature_analysis.html\n")

    def print_feature_importance(self):
        feature_importance = self.regressor.get_feature_importance(prettified=True)
        print(feature_importance)

    def print_test_results(self, df: pd.DataFrame):
        confusion_matrix = pd.crosstab(
            df["Label"],
            df["Label_predicted"].round(),
            rownames=["Actual"],
            colnames=["Predicted"],
        )
        print("\n" + str(confusion_matrix) + "\n")

        df["res"] = df["Label"] == df["Label_predicted"].round()
        print("\n" + str(df["res"].value_counts(normalize=True)) + "\n")

    def print_prc(self, df: pd.DataFrame):
        # calculate precision and recall
        precision, recall, thresholds = precision_recall_curve(df["Label"], df["Label_predicted"])
        thresholds = np.append(thresholds, np.NaN)

        # create precision recall curve
        fig, ax = plt.subplots()
        sc = plt.scatter(recall, precision)
        plt.plot(recall, precision)

        annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->"),
        )
        annot.set_visible(False)

        def update_annot(ind):
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            i = ind["ind"][0]
            annot.set_text(f"t={str(thresholds[i])[:4]}, p={str(precision[i])[:4]}, r={str(recall[i])[:4]}")
            annot.get_bbox_patch().set_alpha(0.4)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = sc.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)

        # Add axis labels to plot
        ax.set_title("Precision-Recall Curve")
        ax.set_ylabel("Precision (accuracy on posts kept)")
        ax.set_xlabel("Recall (percentage of counterfeit retrieved)")

        # Display plot
        plt.show()

    def print_prc_per_brand_with_fixed_recall(self, df: pd.DataFrame, r: float = 0.98):
        result = pd.DataFrame(columns=["threshold", "recall", "precision", "percentage of reject"])
        if "f_cat_organisation__name" in df.columns:
            for org in df["f_cat_organisation__name"].unique():
                org_df = df[:][df["f_cat_organisation__name"] == org]
                precision, recall, thresholds = precision_recall_curve(org_df["Label"], org_df["Label_predicted"])

                index = np.argmin(np.abs(recall - r))
                selected_precision = precision[index]
                selected_threshold = thresholds[index]

                num_rejected = len(org_df[org_df["Label_predicted"] < selected_threshold])
                num_total = len(org_df)

                result = pd.concat(
                    [
                        result,
                        pd.DataFrame(
                            {
                                "threshold": selected_threshold,
                                "recall": r,
                                "precision": selected_precision,
                                "percentage of reject": num_rejected / num_total,
                            },
                            index=[org],
                        ),
                    ]
                )

        avg = result.mean()
        result.loc["Average for all brands"] = avg

        print(f"\nWhen recall = {r}")
        print(result)

    def print_prc_per_brand_with_fixed_threshold(self, df: pd.DataFrame, t: float = 0.2):
        result = pd.DataFrame(columns=["threshold", "recall", "precision"])
        if "f_cat_organisation__name" in df.columns:
            for org in df["f_cat_organisation__name"].unique():
                org_df = df[:][df["f_cat_organisation__name"] == org]
                precision, recall, thresholds = precision_recall_curve(org_df["Label"], org_df["Label_predicted"])

                index = np.argmin(np.abs(thresholds - t))
                selected_precision = precision[index]
                selected_recall = recall[index]

                num_rejected = len(org_df[org_df["Label_predicted"] < t])
                num_total = len(org_df)

                result = pd.concat(
                    [
                        result,
                        pd.DataFrame(
                            {
                                "threshold": t,
                                "recall": selected_recall,
                                "precision": selected_precision,
                                "percentage of reject": num_rejected / num_total,
                            },
                            index=[org],
                        ),
                    ]
                )

        avg = result.mean()
        result.loc["Average for all brands"] = avg

        print(f"\nWhen threshold = {t}")
        print(result)

    def print_hyperparams(self):
        result = self.regressor.get_all_params()
        print(f"Hyperparameters: {result}")

    def load_df(self, path: Path):
        df = pd.read_csv(path, sep="\t")
        return df.loc[:, ~df.columns.str.contains("^Unnamed")]

    def analyse(self, df: pd.DataFrame):
        self.print_feature_importance()
        self.feature_analysis()
        self.print_test_results(df=df)
        self.print_prc(df=df)
        self.print_prc_per_brand_with_fixed_recall(df=df)
        # self.print_prc_per_brand_with_fixed_threshold(df=df)
        self.print_hyperparams()


class PredictionRunner:
    def __init__(self, model_name: str, feature_registry: FeatureRegistry) -> None:
        self.path = MODELS_PATH / "production" / model_name
        self.model_path = self.path / "model"
        self.prediction_df_path = self.path / "prediction_df.csv"

        self.model = Model(model_name=model_name, path=self.path, feature_registry=feature_registry)
        self.prediction_df = self.model.load_df(self.prediction_df_path)

    def analyse_model(self):
        self.model.analyse(df=self.prediction_df)

    def predict(self, posts: pd.DataFrame):
        self.prediction_df = posts  # TODO: remove use of prediction_df
        self.model.compute_features(self.prediction_df)
        self.prediction_df["Label_predicted"] = self.model.predict(df=self.prediction_df)

    def get_good_predictions_sample(self, rows: int) -> Dict[str, int]:
        good_rows = int(0.8 * rows)
        other_rows = rows - good_rows

        top_predictions = (
            self.prediction_df.sort_values(by=["Label_predicted"], ascending=False).head(good_rows).to_dict("records")
        )
        other_predictions = (
            self.prediction_df.drop(
                self.prediction_df.sort_values(by=["Label_predicted"], ascending=False).head(good_rows).index
            )
            .sample(frac=1)
            .head(other_rows)
            .to_dict("records")
        )

        return {post["id"]: post["Label_predicted"] for post in top_predictions + other_predictions}

    def get_prediction(self):
        return {post["id"]: post for post in self.prediction_df.to_dict("records")}


class TrainingRunner:
    def __init__(
        self,
        feature_set: EnumeratedFeatureSet = None,
        model_name: str = None,
        feature_registry: FeatureRegistry = None,
        label_to_prediction: Dict = LABEL_TO_PREDICTION,
        depth=None,
        iterations=None,
        learning_rate=None,
        od_type=None,
        od_wait=None,
        use_best_model=False,
        grid=None,
        use_params_search=False,
    ) -> None:
        log.info("Initializing TrainingRunner")

        self.label_to_prediction = label_to_prediction

        assert feature_set or (feature_registry and model_name)
        model_name = model_name if model_name else str(int(time.time()))

        mode = "training" if feature_set else "production"
        path = MODELS_PATH / mode / model_name

        self.train_df_path = path / "training_df.csv"
        self.eval_df_path = path / "validation_df.csv"
        self.prediction_df_path = path / "prediction_df.csv"

        self.model = Model(
            model_name=model_name,
            path=path,
            feature_set=feature_set,
            feature_registry=feature_registry,
            depth=depth,
            iterations=iterations,
            learning_rate=learning_rate,
            od_type=od_type,
            od_wait=od_wait,
            use_best_model=use_best_model,
            grid=grid,
            use_params_search=use_params_search,
        )
        self.use_params_search = use_params_search

    def build_df(self, dataset: Dataset):
        log.info("Building dataframe")

        dataset.posts = dataset.posts.fillna(value=np.nan)
        self.model.compute_features(dataset.posts)
        dataset.posts["Label"] = dataset.posts["label_name"].apply(lambda x: self.label_to_prediction[x])

        return dataset.posts

    def train(self, dataset: Dataset):
        if self.use_params_search:
            train_dataset = dataset
            self.eval_df = None
        else:
            train_dataset, eval_dataset = dataset.split(frac=0.8)
            self.eval_df = self.build_df(eval_dataset)
            self.eval_df.to_csv(self.eval_df_path, sep="\t")

        self.train_df = self.build_df(train_dataset)
        self.train_df.to_csv(self.train_df_path, sep="\t")

        if self.use_params_search:
            self.model.params_search(df=self.train_df)
        else:
            self.model.train(df=self.train_df, val_df=self.eval_df)

    def test(self, dataset: Dataset):
        self.prediction_df = self.build_df(dataset)
        self.prediction_df["Label_predicted"] = self.model.predict(df=self.prediction_df)
        self.prediction_df.to_csv(self.prediction_df_path, sep="\t")

    def analyse_model(self):
        self.model.analyse(df=self.prediction_df)
