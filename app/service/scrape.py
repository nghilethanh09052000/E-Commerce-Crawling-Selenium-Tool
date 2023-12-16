from app import logger
from app.dao import RedisDAO, WebsiteDAO
from app.models.enums import ScrapingType
from app.settings import sentry_sdk

website_DAO = WebsiteDAO()
redis_DAO = RedisDAO()


def scrape(
    scraper_module,
    domain_name: str,
    scraping_type: ScrapingType,
    **args,
):
    """Run domain scraping"""

    # Check whether the domain exists
    website = website_DAO.get(domain_name)

    if not website:
        logger.info(f"Domain name {domain_name} is currently not available!")
        sentry_sdk.capture_exception(f"Domain name {domain_name} is currently not available!")
        return False

    if scraper_module:
        scraper = scraper_module(
            domain_name=domain_name,
            scraping_type=scraping_type,
            **args,
        )
        return scraper.run()

    return True
