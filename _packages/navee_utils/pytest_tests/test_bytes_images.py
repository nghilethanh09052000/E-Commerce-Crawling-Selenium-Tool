import ast
from io import BytesIO

from PIL import Image
import pytest
import pandas as pd
import numpy as np
from imagehash import phash

from navee_utils.image import url_to_bytes, bytes_to_img, resize_image

"""
### save the size of image

# def get_image_size_from_url(url):
#     img_array = bytes_to_img(url_to_bytes(url))
#     return img_array.shape

# df = pd.read_csv("./pytest_tests/dataset/test.csv", header=0, index_col=0)
# df['img_size'] = df["s3_url"].apply(lambda x: get_image_size_from_url(x))
# df.to_csv("./pytest_tests/dataset/test.csv")
"""

# create testing samples
df = pd.read_csv("./pytest_tests/dataset/test.csv", header=0, index_col=0)
urls = df["s3_url"].values.tolist()
urls_and_img_size = df[["s3_url", "img_size"]].values.tolist()
urls_and_img_size = [(row[0], ast.literal_eval(row[1])) for row in urls_and_img_size]


class TestBytesImages:
    @staticmethod
    @pytest.mark.parametrize("url, img_size", urls_and_img_size)
    def test_bytes_to_img(url, img_size):
        img_bytes = url_to_bytes(url)
        img_array = bytes_to_img(img_bytes)
        assert (
            type(img_array) == np.ndarray
            and img_array.shape == img_size
            and 0 not in img_array.shape
        )

    @staticmethod
    @pytest.mark.parametrize("url", urls)
    def test_resize_image(url):
        img_bytes = url_to_bytes(url)
        new_img_bytes = resize_image(img_bytes)
        phash_old = phash(Image.open(BytesIO(img_bytes)), hash_size=8)
        phash_new = phash(Image.open(BytesIO(new_img_bytes)), hash_size=8)
        assert (
            type(new_img_bytes) == bytes
            and len(new_img_bytes) <= 10 * 1024 * 1024
            and abs(phash_new - phash_old) < 3
        )
