from typing import List, Optional

from sqlalchemy.orm import Query
import numpy as np
import pandas as pd
import requests
import boto3

from automated_moderation.utils.logger import log
from navee_utils.image import upload_image
from automated_moderation.specific_scraper.settings import (
    SS_AWS_ACCESS_KEY_ID,
    SS_AWS_SECRET_ACCESS_KEY,
    SPECIFIC_SCRAPER_AWS_BUCKET,
)

s3 = boto3.client(
    "s3",
    aws_access_key_id=SS_AWS_ACCESS_KEY_ID,
    aws_secret_access_key=SS_AWS_SECRET_ACCESS_KEY,
)


def chunks(lst: List, n: int):
    """Yield successive n-sized chunks from lst"""

    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def query_by_batch(query: Query, batch_size: int = 25000, limit: Optional[int] = None) -> List:
    all_posts = []
    index = 0
    while True:
        log.info(f"Loading batch {index + 1}...")
        batch_limit = batch_size if limit is None else min(batch_size, limit - len(all_posts))
        new_posts = query.limit(batch_limit).offset(index * batch_size).all()
        all_posts.extend(new_posts)

        if len(new_posts) < batch_size:
            break

        index += 1

    return all_posts


def reduce_mem_usage(df: pd.DataFrame) -> pd.DataFrame:
    numerics = ["int16", "int32", "int64", "float16", "float32", "float64"]

    start_mem = df.memory_usage(index=False).sum() / 1024**2
    for col in df.columns:
        col_type = df[col].dtypes
        if col_type in numerics:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == "int":
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float16)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)

    end_mem = df.memory_usage(index=False).sum() / 1024**2
    log.info("Decreased memory by {:.1f}%".format(100 * (start_mem - end_mem) / start_mem))

    return df


def upload_image_from_url(url: str, path: str = "images") -> Optional[str]:
    try:
        img = requests.get(
            url,
            timeout=15,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:84.0) Gecko/20100101 Firefox/84.0",
            },
            verify=False,
        ).content
    except Exception:
        return

    return upload_image(
        s3_client=s3,
        bucket=SPECIFIC_SCRAPER_AWS_BUCKET,
        path=path,
        img=img,
    )
