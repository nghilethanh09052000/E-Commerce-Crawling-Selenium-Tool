from ultralytics import YOLO
import numpy as np
from PIL import Image
import requests
from io import BytesIO


def predict(image_url: str):
    model = YOLO("yolov8n.pt")
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    image = np.asarray(image)
    results = model.predict(image)

    objects_detected = {}
    for result in results:
        for box in result.boxes:
            if box.conf > 0:
                objects_detected[result.names[int(box.cls)]] = float(box.conf)

    # for r in results:
    #     im_array = r.plot()  # plot a BGR numpy array of predictions
    #     im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
    #     im.show()  # show image
    #     im.save('results.jpg')  # save image
    print(image_url)
    print(objects_detected)


if __name__ == "__main__":
    images = [
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/celine/bf973a2c-847b-4619-93b0-802936fecde6.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/d8959e0cfb69af505d9e2e97e8dcaeffbb2b5c9177bfd7f8d3fb90c8449f194b.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/494e6fd3-77ff-49ea-82bb-671e57f88ba4.jpeg",
        "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/gucci/7704b358-6065-4341-a40e-03254204904d.jpeg",
    ]

    for image in images:
        predict(image)
