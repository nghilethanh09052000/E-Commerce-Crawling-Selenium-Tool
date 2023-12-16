from app.dao import PostDAO
from .api_scraper import APIScraper

post_DAO = PostDAO()


class APIMarketplaceScraper(APIScraper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if self.config.search_pages_browsing_module.name != "search_only_browsing_module":
            self.batch_size = 2

    def _scrape(self):
        super(APIScraper, self)._scrape()
