from typing import Dict, Optional
from pathlib import Path
import csv

import pandas as pd
from rich.progress import track

from . import Feature, FeatureRegistry


# see https://catboost.ai/en/docs/concepts/input-data_column-descfile
FTYPE_TO_CATBOOST = {
    "f_label": "Label",
    "f_num": "Num",
    "f_cat": "Categ",
    "f_text": "Text",
    "f_aux": "Auxiliary",
    "f_id": "SampleId",
}


class EnumeratedFeatureSet:
    def __init__(
        self,
        features: Dict[str, Feature] = None,
        load_from_path: Optional[str] = None,
        feature_registry: Optional[FeatureRegistry] = None,
    ):
        self.features_dict = self.load_from_path(load_from_path, feature_registry) if load_from_path else features

        # 0th feature is always the label
        self.features_list = [Feature("f_label")] + list(f for f in self.features_dict.values())
        self.name_to_index = dict((self.features_list[index], index) for index in range(len(self.features_list)))
        self.index_to_name = dict((index, self.features_list[index].name) for index in range(len(self.features_list)))

    @staticmethod
    def load_from_path(path: str, feature_registry: Optional[FeatureRegistry]) -> Dict[str, Feature]:
        # TODO: Add sanity check
        features = {}
        with open(path, "r") as csvfile:
            columns_description = csv.reader(csvfile, delimiter="\t")
            next(columns_description)  # Skip first line (f_label)
            for row in columns_description:
                features[row[2]] = feature_registry.get_by_name(row[2])
        return features

    def get_feature_names(self):
        return list(self.features_dict.keys())

    def create_columns_description(self, path: Path):
        Path(path.parent).mkdir(parents=True, exist_ok=True)

        # Catboost create_cd is very inconvenient, see: https://github.com/catboost/catboost/issues/2193

        # catboost.utils.create_cd(
        #    label = 0,
        #    cat_features = list( i for i in range(len(self.features_list)) if self.features_list[i].ftype == 'f_cat'),
        #    auxiliary_columns = list( i for i in range(len(self.features_list)) if self.features_list[i].ftype == 'f_aux'),
        #    feature_names = self.index_to_name,
        #    output_path = path,
        # )

        # And anyway it's much easier to generate the end-result directly, we almost have it already
        with open(path, "w") as f:
            for index in range(len(self.features_list)):
                feature = self.features_list[index]
                f.write("{}\t{}\t{}\n".format(index, FTYPE_TO_CATBOOST[feature.ftype], feature.name))

    def to_df(self, posts: pd.DataFrame) -> pd.DataFrame:
        features = list(self.features_dict.values())
        for feature in track(features, description="Computing features"):
            feature.df_to_feature(posts)
