from navee_logging import NaveeLogger, NaveeModule

from app.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    ENVIRONMENT_NAME,
)

logger = NaveeLogger(
    NaveeModule.INFEX_WORKER,
    aws_access_key=AWS_ACCESS_KEY_ID,
    aws_secret_key=AWS_SECRET_ACCESS_KEY,
    aws_region=AWS_REGION,
    override=True,
    dev=(ENVIRONMENT_NAME == 'development'),
)
