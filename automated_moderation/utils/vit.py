from typing import List, Dict

import torch
from PIL import Image
import requests

from automated_moderation.Cream.TinyViT.models.tiny_vit import tiny_vit_5m_224
from automated_moderation.Cream.TinyViT.data import build_transform, imagenet_classnames
from automated_moderation.Cream.TinyViT.config import get_config

config = get_config()
transform = build_transform(is_train=False, config=config)


# Build model
model = tiny_vit_5m_224(pretrained=True)
model.eval()


def predict(image_url: str) -> Dict[str, float]:
    try:
        image = Image.open(
            requests.get(
                image_url,
                stream=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
                },
            ).raw
        )

        # (1, 3, img_size, img_size)
        batch = transform(image)[None]

        with torch.no_grad():
            logits = model(batch)

        # print top-5 classification names
        probs = torch.softmax(logits, -1)
        scores, inds = probs.topk(5, largest=True, sorted=True)
        predictions = {}
        for score, ind in zip(scores[0].numpy(), inds[0].numpy()):
            predictions[imagenet_classnames[ind]] = score

        return predictions
    except Exception:
        pass


def predict_urls(image_urls=List[str]) -> Dict[str, str]:
    predictions = {}
    for image_url in image_urls:
        predictions[image_url] = predict(image_url)

    return predictions


if __name__ == "__main__":
    images = [
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/celine/bf973a2c-847b-4619-93b0-802936fecde6.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/d8959e0cfb69af505d9e2e97e8dcaeffbb2b5c9177bfd7f8d3fb90c8449f194b.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/494e6fd3-77ff-49ea-82bb-671e57f88ba4.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/7704b358-6065-4341-a40e-03254204904d.jpeg",
    ]

    print(predict_urls(images))
