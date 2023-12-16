from typing import List, Dict

import torch
import requests
from PIL import Image
from lavis.models import load_model_and_preprocess


# setup device to use
device = torch.device("cuda") if torch.cuda.is_available() else "cpu"
model, vis_processors, _ = load_model_and_preprocess(
    name="blip2_opt", model_type="caption_coco_opt2.7b", is_eval=True, device=device
)


def predict(raw_image: Image) -> str:
    image = vis_processors["eval"](raw_image).unsqueeze(0).to(device)
    print(model.generate(image))
    exit()


def predict_urls(image_urls=List[str]) -> Dict[str, str]:
    predictions = {}
    for image_url in image_urls:
        img = Image.open(
            requests.get(
                image_url,
                stream=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
                },
            ).raw
        )

        predictions[image_url] = predict(img)

    return predictions


if __name__ == "__main__":
    images = [
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/d8959e0cfb69af505d9e2e97e8dcaeffbb2b5c9177bfd7f8d3fb90c8449f194b.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/494e6fd3-77ff-49ea-82bb-671e57f88ba4.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/7704b358-6065-4341-a40e-03254204904d.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/c840aefe-7f9d-4a7b-917c-9cf8ac252a26.png",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/68d292fe-cc16-4a79-b238-41cdb94d35c4.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/a4f430dd-d133-4dcd-8173-e9cd40aeb0a2.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/b3f9689a-8f3e-4994-a504-126593351628.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/f86ad9fd329efa84cb7247c4db58300620b04825a5b3e7bb13aacc1e566332c0.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/5816e1b5-b007-41dd-9db9-5c6fdec4c6a4.jpeg",
        # "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/2bcfb139-ce97-4f3d-a629-8bd3e36dc36c.jpeg",
    ]

    predict_urls(images)
