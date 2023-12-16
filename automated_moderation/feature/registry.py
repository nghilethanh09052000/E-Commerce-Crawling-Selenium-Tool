from typing import Set, List

from .feature import Feature


class FeatureRegistry:
    def __init__(self, features: List[Feature] = []):
        self.features = {f.name: f for f in features}

    def add_feature(self, f: Feature):
        if f.name in self.features:
            raise ValueError(f"Duplicate feature {f.name}")
        self.features[f.name] = f

    def add_features(self, *features: Feature):
        for f in features:
            self.add_feature(f)

    def add(self, name: str, description: str = "", default_value: str = "-1", tags: Set[str] = set()):
        self.add_feature(Feature(name, description, default_value, tags))

    def get_slice(self, include_tags: Set[str], exclude_tags: Set[str]):
        return dict(
            (name, value) for name, value in self.features.items() if value.is_good_for_tags(include_tags, exclude_tags)
        )

    def get_by_name(self, f_name: str) -> Feature:
        return self.features[f_name]
