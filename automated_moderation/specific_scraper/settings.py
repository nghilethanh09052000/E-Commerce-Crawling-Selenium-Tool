import os

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.ss")

# Database settings
SS_DB_NAME = os.getenv("SS_DB_NAME")
SS_DB_HOST = os.getenv("SS_DB_HOST")
SS_DB_USER = os.getenv("SS_DB_USER")
SS_DB_PASSWORD = os.getenv("SS_DB_PASSWORD")
SS_DB_PORT = os.getenv("SS_DB_PORT")

SS_AWS_ACCESS_KEY_ID = os.getenv("SS_AWS_ACCESS_KEY_ID")
SS_AWS_SECRET_ACCESS_KEY = os.getenv("SS_AWS_SECRET_ACCESS_KEY")
SPECIFIC_SCRAPER_AWS_BUCKET = os.getenv("SS_SPECIFIC_SCRAPER_AWS_BUCKET")
