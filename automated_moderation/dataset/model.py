from typing import Union, List, Optional, Dict
from dataclasses import dataclass, field, asdict, is_dataclass
import json

import re
from datetime import datetime


class DeserializableDataclass:
    @classmethod
    def from_json(cls, data):
        for key in data:
            if isinstance(data[key], list) and is_dataclass(cls.__annotations__[key].__args__[0]):
                _type = cls.__annotations__[key].__args__[0]
                data[key] = [_type.from_json(d) for d in data[key]]

            if isinstance(data[key], dict) and (
                (hasattr(cls.__annotations__[key], "__args__") and is_dataclass(cls.__annotations__[key].__args__[0]))
                or (
                    hasattr(cls.__annotations__[key], "__origin__")
                    and cls.__annotations__[key].__origin__ == list
                    and is_dataclass(cls.__annotations__[key].__args__[0])
                )
                or is_dataclass(cls.__annotations__[key])
            ):
                _type = (
                    cls.__annotations__[key].__args__[0]
                    if hasattr(cls.__annotations__[key], "__args__")
                    else cls.__annotations__[key]
                )
                data[key] = _type.from_json(data[key])

        return cls(**data)

    def to_json(self):
        def json_encoder(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()

            return obj.__dict__

        return json.dumps(self, default=lambda o: json_encoder(o))


@dataclass
class BaseOrganisation(DeserializableDataclass):
    name: str


@dataclass
class BasePoster(DeserializableDataclass):
    id: Optional[Union[int, str]] = None
    url: Optional[str] = None
    name: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    profile_pic_url: Optional[str] = None
    archive_link: Optional[str] = None
    followers_count: Optional[int] = None
    total_infringing_posts_for_org: Optional[int] = None
    total_posts_for_org: Optional[int] = None
    total_infringing_posts: Optional[int] = None
    total_posts: Optional[int] = None
    website_identifier: Optional[str] = None
    cluster_total_infringing_posts_for_org: Optional[int] = None
    cluster_total_posts_for_org: Optional[int] = None
    cluster_total_infringing_posts: Optional[int] = None
    cluster_total_posts: Optional[int] = None


@dataclass
class BaseCategory(DeserializableDataclass):
    name: str


@dataclass
class BaseImage(DeserializableDataclass):
    logo_detected: Optional[bool] = None
    s3_url: Optional[str] = None
    url: Optional[str] = None
    logo_predictions: Optional[List[str]] = None


@dataclass
class BaseWebsite(DeserializableDataclass):
    domain_name: str
    website_category: Optional[str]


@dataclass
class BasePost(DeserializableDataclass):
    id: Union[int, str]
    images: List[BaseImage] = field(default_factory=list)
    title: Optional[str] = None
    description: Optional[str] = None
    organisation: Optional[BaseOrganisation] = None
    url: Optional[str] = None
    translated_title: Optional[str] = None
    translated_description: Optional[str] = None
    source_language: Optional[str] = None
    category: Optional[BaseCategory] = None
    poster: Optional[BasePoster] = None
    website: Optional[BaseWebsite] = None
    label_name: Optional[str] = None
    weight: float = 1
    is_desc_counterfeit: Optional[bool] = None
    created_at: Optional[datetime] = None
    search_query: Optional[str] = None
    features: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    skip_filter_scraped_results: bool = False
    valid_organisations: List[str] = field(default_factory=list)
    risk_score: Dict = field(default_factory=dict)
    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    hashtags: Optional[List[str]] = None
    archive_link: Optional[str] = None

    def __post_init__(self):
        self.set_text_features()

    def set_text_features(self):
        HASHTAG_REGEX = r"\#\w*"

        original_title = self.title or ""
        original_description = self.description or ""
        original_text_with_hashtags = original_title + "\n" + original_description
        self.original_text = re.sub(HASHTAG_REGEX, "", original_text_with_hashtags)

        translated_title = self.translated_title or ""
        translated_description = self.translated_description or ""
        translated_text_with_hashtags = translated_title + "\n" + translated_description
        self.translated_text = re.sub(HASHTAG_REGEX, "", translated_text_with_hashtags)

        self.hashtags = re.findall(HASHTAG_REGEX, original_text_with_hashtags)

        self.translated_text = self.translated_text.replace("\t", " ") if self.translated_text else ""
        self.original_text = self.original_text.replace("\t", " ") if self.original_text else ""

        self.translated_title = self.translated_title.replace("\t", " ") if self.translated_title else ""
        self.title = self.title.replace("\t", " ") if self.title else ""

        self.translated_description = (
            self.translated_description.replace("\t", " ") if self.translated_description else ""
        )
        self.description = self.description.replace("\t", " ") if self.description else ""

    @property
    def serialize(self):
        return {k: (str(v) if not is_dataclass(v) else asdict(v)) for k, v in asdict(self).items()}
