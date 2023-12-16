from dotenv import load_dotenv
import os
from redis import Redis


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

REDIS_SCRAPER_INSERTION = os.getenv("REDIS_SCRAPER_INSERTION")
REDIS_SCRAPER_PORT = int(os.getenv("REDIS_SCRAPER_PORT", 6379))

redis = Redis(
    host=REDIS_SCRAPER_INSERTION,
    port=REDIS_SCRAPER_PORT,
    decode_responses=True,
    socket_timeout=5,
)

# Lambda interface
LAMBDA_API_KEY = os.getenv("LAMBDA_API_KEY")
