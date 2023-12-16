from typing import Optional
from io import BytesIO
from uuid import uuid4
from botocore.exceptions import ClientError

BASE_PATH_S3 = "https://s3-eu-west-1.amazonaws.com"


def upload_html_file(s3_client, bucket: str, path: str, file: bytes) -> Optional[str]:
    try:
        file_path = f'{path}/{uuid4()}.html'
        s3_client.upload_fileobj(
            BytesIO(file),
            bucket,
            file_path,
            ExtraArgs={"ACL": "public-read", "ContentType": "application/octet-stream"},
        )
        return f"{BASE_PATH_S3}/{bucket}/{file_path}"
    except ClientError:
        return