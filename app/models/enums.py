from enum import Enum, auto


class ScrapingType(Enum):
    POST_SEARCH_COMPLETE = auto()  # Search and return a list of posts from search queries or hashtags
    POST_SEARCH_COUNT_ONLY = auto()  # Search and return the number of results per keywords
    POST_SEARCH_RADARLY = auto()  # Search and return a list of posts from Radarly queries
    POST_SCRAPE_FROM_LIST = auto()  # Retrieve posts from list, by post ID for Instagram
    POSTER_SEARCH = auto()  # Scrape account info & posts
    POST_IMAGE_SEARCH_COMPLETE = auto()


class SEARCH_FRAMEWORKS(Enum):
    SELENIUM = "selenium_framework"
    API = "api_framework"
    API_SELENIUM = "api_selenium_framework"


class DataSource(Enum):
    SPECIFIC_SCRAPER = auto()
    RISE_RECRAWLING = auto()
    MANUAL_INSERTION = auto()
    YUPOO_SCRAPER = auto()
    RUSSIAN_RADARLY = auto()
    RADARLY = auto()
    OTHER = auto()
    SMELTER_AI = auto()
    API_SCRAPER = auto()


# What is the Type of the url scraped
class UrlPageType(Enum):
    SEARCH = auto()
    POST = auto()
    POSTER = auto()


class RequestResult(Enum):
    SUCCESS = auto()
    TIMEOUT = auto()
    DRIVER_FAILURE = auto()
    PROXY_FAILURE = auto()
    SCRAPING_FAILURE = auto()
    OTHER_FAILURE = auto()


class ScrapingActionType(Enum):
    ARCHIVING = auto()
    SCRAPING = auto()


class ScrapingStatus(Enum):
    SEARCHED = auto()
    FILTERED_IN = auto()
    FILTERED_OUT = auto()  # rejected
    SCRAPED = auto()
    SENT = auto()
