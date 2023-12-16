from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass

from automated_moderation.dataset import BasePost
from automated_moderation.utils.logger import log


@dataclass
class PostGetter(ABC):
    @abstractmethod
    def get(
        self, organisation_name: Optional[str] = None, domain_name: Optional[str] = None, tag: Optional[str] = None
    ) -> List[BasePost]:
        pass

    def detect_logos(self, posts: List[BasePost], organisation_name: Optional[str] = None):
        log.info("Predicting logos...")

        from automated_moderation.utils.logo_detection import get_brands_from_image_url

        image_urls = [
            image.s3_url if image.s3_url else image.url
            for post in posts
            for image in post.images
            if image.logo_predictions is None
        ]

        while True:
            logo_predictions = get_brands_from_image_url(image_urls=image_urls, organisation_name=organisation_name)

            for post in posts:
                for image in post.images:
                    image_url = image.s3_url if image.s3_url else image.url
                    if image.logo_predictions is None and image_url in logo_predictions:
                        image.logo_predictions = logo_predictions[image_url]
                        image.logo_detected = (
                            organisation_name in image.logo_predictions
                            if organisation_name and image.logo_predictions is not None
                            else None
                        )

            new_image_urls = [
                image.s3_url if image.s3_url else image.url
                for post in posts
                for image in post.images
                if image.logo_predictions is None
            ]

            if not new_image_urls or len(new_image_urls) >= len(image_urls):
                break

            image_urls = new_image_urls
