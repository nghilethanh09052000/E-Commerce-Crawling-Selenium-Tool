import logging
import os

import boto3
import sentry_sdk
from dotenv import load_dotenv
from radarly import RadarlyApi
from redis import Redis
from requests.exceptions import ConnectionError
from sentry_sdk.integrations.logging import LoggingIntegration
from lambda_ip.get_ip import API_KEY as GET_IP_API_KEY


UPLOAD_REQUEST_EXPIRY = 3600 * 48
PROFILES_BATCH_SIZE = 200
PROFILES_BATCH_EXPIRY = 3600 * 24
DOMAIN_WHO_IS_EXPIRY = 3600 * 24 * 7  # 7 days
DOMAIN_BUILT_WITH_EXPIRY = 3600 * 24 * 30  # 1 month
URL_LOG_WITH_EXPIRY = 3600 * 24 * 30  # 1 month

ENVIRONMENT_NAME = os.getenv("ENVIRONMENT_NAME")
print("ENVIRONMENT_NAME: {}".format(ENVIRONMENT_NAME))

DEBUG = os.getenv("DEBUG", False)

if ENVIRONMENT_NAME == "production":
    load_dotenv(dotenv_path=".env.production")

elif ENVIRONMENT_NAME == "production_bastion":

    # Environment variables which allow accessing the production database and Redis server through bastions
    load_dotenv(dotenv_path=".env.production")
    load_dotenv(dotenv_path=".env.production_bastion", override=True)

    # We need to set the ENVIRONMENT_NAME to production in particular because we pass the environment name when running ECS tasks
    ENVIRONMENT_NAME = "production"

elif ENVIRONMENT_NAME == "development":
    load_dotenv(dotenv_path=".env.development", verbose=True)
    DEBUG = True

else:
    raise EnvironmentError("The ENVIRONMENT_NAME is not set or not valid")

# Sentry
DSN_SENTRY = os.getenv("DSN_SENTRY")
print(f"APP Sentry DNS {DSN_SENTRY}")
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
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

AWS_COUNTERFEIT_ACCESS_KEY_ID = os.getenv("AWS_COUNTERFEIT_ACCESS_KEY_ID")
AWS_COUNTERFEIT_SECRET_ACCESS_KEY = os.getenv("AWS_COUNTERFEIT_SECRET_ACCESS_KEY")

AWS_RISE_ACCESS_KEY_ID = os.getenv("AWS_RISE_ACCESS_KEY_ID")
AWS_RISE_SECRET_ACCESS_KEY = os.getenv("AWS_RISE_SECRET_ACCESS_KEY")

AWS_RECRAWLING_QUEUE = os.getenv("AWS_RECRAWLING_QUEUE")
AWS_SUBNETS = os.getenv("AWS_SUBNETS").split(",")
AWS_GENERAL_SECURITY_GROUP = os.getenv("AWS_GENERAL_SECURITY_GROUP").split(",")
AWS_ROTATING_PROXY_SUBNET = os.getenv("AWS_ROTATING_PROXY_SUBNET").split(",")
AWS_ROTATING_PROXY_SECURITY_GROUP = os.getenv("AWS_ROTATING_PROXY_SECURITY_GROUP").split(",")

SPECIFIC_SCRAPER_AWS_BUCKET = os.getenv("SPECIFIC_SCRAPER_AWS_BUCKET")
COUNTERFEIT_PLATFORM_INSERTION_QUEUE = os.getenv("COUNTERFEIT_PLATFORM_INSERTION_QUEUE")
SCRAPING_QUEUE = os.getenv("SCRAPING_QUEUE")

REDIS_SCRAPER_INSERTION = os.getenv("REDIS_SCRAPER_INSERTION")
REDIS_SCRAPER_PORT = int(os.getenv("REDIS_SCRAPER_PORT", 6379))

redis = Redis(
    host=REDIS_SCRAPER_INSERTION,
    port=REDIS_SCRAPER_PORT,
    decode_responses=True,
    socket_timeout=5,
)

# AWS SQS
boto_session = boto3.session.Session(
    region_name=AWS_REGION,
    aws_access_key_id=AWS_COUNTERFEIT_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_COUNTERFEIT_SECRET_ACCESS_KEY,
)

sqs_client = boto_session.resource("sqs", endpoint_url="https://sqs.eu-west-1.amazonaws.com")

sqs_client_scraping = boto3.resource(
    "sqs",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url="https://sqs.eu-west-1.amazonaws.com",
)

# Database settings
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

# Application credentials
BASIC_AUTH_USERNAME = os.getenv("BASIC_AUTH_USERNAME")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD")

# Radarly API
RADARLY_CLIENT_ID = os.getenv("RADARLY_CLIENT_ID")
RADARLY_CLIENT_SECRET = os.getenv("RADARLY_CLIENT_SECRET")

# Initialize the API client
if RADARLY_CLIENT_ID:
    try:
        RadarlyApi.init(client_id=RADARLY_CLIENT_ID, client_secret=RADARLY_CLIENT_SECRET)
    except ConnectionError:
        # In very rare cases, the Radarly API initialization fails
        # We just ignore the case because an error will later be raised if ever we need to use the API
        pass

# Rotating proxy setup
ROTATING_PROXY_IP = os.getenv("ROTATING_PROXY_IP")

# Google search configuration
GOOGLE_POST_SEARCH_CX = os.getenv("GOOGLE_POST_SEARCH_CX")
GOOGLE_PROFILE_SEARCH_CX = os.getenv("GOOGLE_PROFILE_SEARCH_CX")
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_KEY")

# API configuration
ML_CACHING_API_KEY = os.getenv("ML_CACHING_API_KEY")
PREFILTERING_API_KEY = os.getenv("PREFILTERING_API_KEY")

# Lambda interface
LAMBDA_API_KEY = os.getenv("LAMBDA_API_KEY")

# api setup
SWAGGER_SCHEME = os.getenv("SWAGGER_SCHEME", "http")
# Image upload
IMAGE_HASH_SALT = os.getenv("IMAGE_HASH_SALT")

# API Authorization key
NAVEE_DRIVER_AUTHORIZATION_KEY = os.getenv("NAVEE_DRIVER_AUTHORIZATION_KEY")
NAVEE_DRIVER_API_URL = os.getenv("NAVEE_DRIVER_API_URL")
NAVEE_DRIVER_API_TIMEOUT = 300

DEFAULT_MAX_POSTS_TO_BROWSE = os.getenv("DEFAULT_MAX_POSTS_TO_BROWSE")

GET_IP_URL = f"https://efm1kr41me.execute-api.eu-west-1.amazonaws.com/ip-lambda?api-key={GET_IP_API_KEY}"
