import hashlib

import pytest
import pandas as pd
import numpy as np

from navee_utils.image import url_to_bytes, url_to_img

IMAGE_HASH_SALT = "SuolVDrtu8zKDihyNgB9COWyEU8DThADDggjcGDgh0zQ17JFMlqY9mUwXnUfmccD"

df = pd.read_csv("./pytest_tests/dataset/test.csv", header=0, index_col=0)

"""
### save current sha256 in csv
#
# def url_to_sha256(url: str) -> str:
#     img_bytes = url_to_bytes(url)
#     img_with_salt = img_bytes + bytes(IMAGE_HASH_SALT, encoding="utf8")
#     return hashlib.sha256(img_with_salt).hexdigest()
#
# df['sha256'] = df["s3_url"].apply(lambda x: url_to_sha256(x))
# df.to_csv("./pytest_tests/dataset/test.csv")
"""

# create testing samples
urls = df["s3_url"].values.tolist()
urls_and_sha256 = df[["s3_url", "sha256"]].values.tolist()
urls_and_sha256 = [(row[0], row[1]) for row in urls_and_sha256]


class TestUrlImages:
    @staticmethod
    @pytest.mark.parametrize("url, sha256", urls_and_sha256)
    def test_url_to_bytes(url, sha256):
        img_bytes = url_to_bytes(url)
        img_with_salt = img_bytes + bytes(IMAGE_HASH_SALT, encoding="utf8")
        hash_result = hashlib.sha256(img_with_salt).hexdigest()
        assert type(img_bytes) == bytes and hash_result == sha256

    @staticmethod
    @pytest.mark.parametrize("url", urls)
    def test_url_to_img(url):
        assert type(url_to_img(url)) == np.ndarray
