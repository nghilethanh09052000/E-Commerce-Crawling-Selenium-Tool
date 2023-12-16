from app.settings import AWS_ACCESS_KEY_ID, AWS_REGION, AWS_SECRET_ACCESS_KEY, ENVIRONMENT_NAME
from navee_logging import NaveeLogger, NaveeModule

logger = NaveeLogger(
    NaveeModule.SPECIFIC_SCRAPER,
    aws_access_key=AWS_ACCESS_KEY_ID,
    aws_secret_key=AWS_SECRET_ACCESS_KEY,
    aws_region=AWS_REGION,
    override=True,
    environment=ENVIRONMENT_NAME,
    dev=(ENVIRONMENT_NAME == "development"),
)
