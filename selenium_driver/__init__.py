from navee_logging import NaveeLogger, NaveeModule

from selenium_driver.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    ENVIRONMENT_NAME,
)

# We need to initialize the logger before loading the app models
logger = NaveeLogger(
    NaveeModule.SPECIFIC_SCRAPER,
    aws_access_key=AWS_ACCESS_KEY_ID,
    aws_secret_key=AWS_SECRET_ACCESS_KEY,
    aws_region=AWS_REGION,
    environment=ENVIRONMENT_NAME,
)
