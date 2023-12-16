# -*- coding: utf-8 -
import os
import logging

import boto3
import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.logging import LoggingIntegration

ENVIRONMENT_NAME = os.getenv("ENVIRONMENT_NAME")
print("DRIVER ENVIRONMENT_NAME: {}".format(ENVIRONMENT_NAME))

dotenv_path = "selenium_driver/"

if ENVIRONMENT_NAME == "production":
    if os.path.basename(os.getcwd()) == "selenium_driver":
        load_dotenv(dotenv_path=".env.production")
    else:
        load_dotenv(dotenv_path="selenium_driver/.env.production")

elif ENVIRONMENT_NAME == "production_bastion":
    # Environment variables which allow accessing the production database and Redis server through bastions
    load_dotenv(dotenv_path=f"{dotenv_path}.env.production")
    load_dotenv(dotenv_path=f"{dotenv_path}.env.production_bastion", override=True)

    # We need to set the ENVIRONMENT_NAME to production in particular because we pass the environment name when running ECS tasks
    ENVIRONMENT_NAME = "production"

elif ENVIRONMENT_NAME == "development":
    load_dotenv(dotenv_path=f"{dotenv_path}.env.development", verbose=True)
else:
    raise EnvironmentError("The ENVIRONMENT_NAME is not set or not valid")


# Installed Chrome Version
CHROME_VERSION = os.getenv("CHROME_VERSION")
if CHROME_VERSION:
    CHROME_VERSION = int(CHROME_VERSION)

# SENTRY
DSN_SENTRY = os.getenv("SELENIUM_DSN_SENTRY")
print(f"Selenium Driver Sentry DNS {DSN_SENTRY}")

SAMPLE_RATE_LOGS = float(os.getenv("SAMPLE_RATE_LOGS"))


sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.ERROR,  # Capture info and above as breadcrumbs  # Send errors as events
)

sentry_sdk.init(
    DSN_SENTRY,
    environment=ENVIRONMENT_NAME,
    sample_rate=SAMPLE_RATE_LOGS,
    release=os.getenv("SENTRY_RELEASE"),
    integrations=[sentry_logging],
)

# AWS
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_COUNTERFEIT_ACCESS_KEY_ID = os.getenv("AWS_COUNTERFEIT_ACCESS_KEY_ID")
AWS_COUNTERFEIT_SECRET_ACCESS_KEY = os.getenv("AWS_COUNTERFEIT_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_RECRAWLING_QUEUE = os.getenv("AWS_RECRAWLING_QUEUE")
AWS_SUBNETS = os.getenv("AWS_SUBNETS").split(",")
AWS_GENERAL_SECURITY_GROUP = os.getenv("AWS_GENERAL_SECURITY_GROUP").split(",")
AWS_ROTATING_PROXY_SUBNET = os.getenv("AWS_ROTATING_PROXY_SUBNET").split(",")
AWS_ROTATING_PROXY_SECURITY_GROUP = os.getenv("AWS_ROTATING_PROXY_SECURITY_GROUP").split(",")

SPECIFIC_SCRAPER_AWS_BUCKET = os.getenv("SPECIFIC_SCRAPER_AWS_BUCKET")

# AWS SQS
boto_session = boto3.session.Session(
    region_name=AWS_REGION,
    aws_access_key_id=AWS_COUNTERFEIT_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_COUNTERFEIT_SECRET_ACCESS_KEY,
)

sqs_client = boto_session.resource("sqs", endpoint_url="https://sqs.eu-west-1.amazonaws.com")


# Crawling parameters
DEFAULT_SCROLL_ATTEMPTS = 10
DEFAULT_SCROLL_PAUSE_TIME = 0.1
DEFAULT_SLEEP_AFTER_GET = 0.5
DEFAULT_SCROLL_SLEEP = 0.5
DEFAULT_SLEEP_AFTER_OPERATIONS = 0.5
DEFAULT_CLOUDFLARE_BYPASS_TIME = 5

DEFAULT_LOADING_DELAY = float(os.getenv("DEFAULT_LOADING_DELAY", 0.5))
DEFAULT_LOADING_TIMEOUT = float(os.getenv("DEFAULT_LOADING_TIMEOUT", 5))
DEFAULT_REQUIRED_LOADING_DELAY = float(os.getenv("DEFAULT_REQUIRED_LOADING_DELAY", 2))
DEFAULT_REQUIRED_LOADING_TIMEOUT = float(os.getenv("DEFAULT_REQUIRED_LOADING_TIMEOUT", 30))
DEFAULT_GET_PAGE_TIMEOUT = float(os.getenv("DEFAULT_GET_PAGE_TIMEOUT", 300))
MAX_GET_PAGE_TIMEOUT = float(os.getenv("MAX_GET_PAGE_TIMEOUT", 600))


DISABLE_XVFB = float(os.getenv("DISABLE_XVFB", 0))

# Rotating proxy setup
ROTATING_PROXY_IP = os.getenv("ROTATING_PROXY_IP")

# Archiving parameters
ARCHIVING_DEFAULT_SLEEP_AFTER_GET = 1.5
ARCHIVING_DEFAULT_SLEEP_AFTER_OPERATIONS = 0.2

ARCHIVING_DEFAULT_START_WINDOW_WIDTH = 1024
ARCHIVING_DEFAULT_START_WINDOW_HEIGHT = 600
ARCHIVING_DEFAULT_SLEEP_AFTER_SET_WINDOW_TO_REQUIRED_SIZE = 0.2

ARCHIVING_SLEEP_AFTER_CLICK_ACTION = 0.5

ARCHIVING_MAX_SCROLL_ACTION = 10
ARCHIVING_TIME_SCROLL_ACTION = 3
ARCHIVING_SCROLL_TOLERANCE_THRESHOLD = 1000
ARCHIVING_DEFAULT_SCROLL_SLEEP = 0.05
ARCHIVING_SLEEP_AFTER_SCROLL_DOWN = 0.5
ARCHIVING_SLEEP_AFTER_SCROLL_UP = 0.5
