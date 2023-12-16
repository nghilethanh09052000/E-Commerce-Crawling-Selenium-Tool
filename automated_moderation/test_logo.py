from automated_moderation.post_getter.from_db import LightPostGetter
from automated_moderation.dataset import BasePost, BaseImage

if __name__ == "__main__":
    image_urls = [
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/e3aa9e91-6937-447b-97bf-e4c65d50d008.webp",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/907db14f-be88-431f-913e-ebcb6b04522b.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/54842a5b-10b4-45ad-83ee-125217831599.webp",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/7f081ba6-235b-4e6f-8520-8c745988a731.webp",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/bccdac70-0372-4971-9f28-889d71bcdc2a.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-platform/production/images/chanel/2e04a54d-1b23-4680-b3ca-9b2853b5c86f.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/1ccfc93d-afbb-40e6-8f55-685998f1f6ac.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-platform/production/images/chanel/bb04cbc5-c9eb-41ce-af6d-22823c794928.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/1c0e1820-41d0-403e-b53f-8ee79275a7e3.webp",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/chanel/ffb2d67a-35b8-422a-b8d2-b757fa481a0a.jpeg",
    ]

    posts = []
    for image_url in image_urls:
        posts.append(BasePost(id=1, images=[BaseImage(url=image_url)]))

    post_getter = LightPostGetter()
    post_getter.detect_logos(posts=posts, organisation_name="Chanel_Navee")

    print(posts)
