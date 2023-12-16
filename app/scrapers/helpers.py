from app.configs.utils import load_config
from app.scrapers import InstagramScraper, MarketplaceScraper, APIScraper, FacebookScraper, APIMarketplaceScraper
from app.models.enums import SEARCH_FRAMEWORKS, DataSource, ScrapingType


def get_scraper_module(domain_name, config=None, scraping_type=None, config_file=None):
    """Main Entry Function to check which scraper Module to choose"""

    if config_file == "smelter.ai":
        return APIScraper, DataSource.SMELTER_AI

    if domain_name == "instagram.com":
        return InstagramScraper, DataSource.RUSSIAN_RADARLY

    if domain_name == "facebook.com" and scraping_type == ScrapingType.POST_SEARCH_COMPLETE:
        return FacebookScraper, DataSource.API_SCRAPER

    if config is None:
        config = load_config(domain_name, load_chrome_profile=False)

    if config.name == SEARCH_FRAMEWORKS.API.value:
        return APIScraper, DataSource.API_SCRAPER
    if config.name == SEARCH_FRAMEWORKS.API_SELENIUM.value:
        return APIMarketplaceScraper, DataSource.API_SCRAPER

    return MarketplaceScraper, DataSource.SPECIFIC_SCRAPER
