import logging
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

ENVIRONMENT_NAME = os.getenv("ENVIRONMENT_NAME")

# In the actual production environment (Lambda function), the environment variables are set upon deployment
if not os.getenv("API_TOKEN"):

    from dotenv import load_dotenv

    if os.path.basename(os.getcwd()) == "russian_radarly":
        load_dotenv(dotenv_path=".env")
    else:
        load_dotenv(dotenv_path="russian_radarly/.env")

API_TOKEN = os.getenv("API_TOKEN")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_SAMPLE_RATE = float(os.getenv("SENTRY_SAMPLE_RATE", "1.0"))
SENTRY_RELEASE = os.getenv("SENTRY_RELEASE")

sentry_logging = LoggingIntegration(
    level=logging.INFO,  # capture info and above as breadcrumbs
    event_level=None,  # don't capture log errors as Sentry events
)

sentry_sdk.init(
    SENTRY_DSN,
    environment=ENVIRONMENT_NAME,
    sample_rate=SENTRY_SAMPLE_RATE,
    release=SENTRY_RELEASE,
    integrations=[sentry_logging],
)
