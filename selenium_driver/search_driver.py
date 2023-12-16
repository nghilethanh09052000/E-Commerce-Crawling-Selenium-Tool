from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium_driver import loader_modules, logger

from .main_driver import Selenium


class SeleniumSearch(Selenium):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def get_urls_from_page(self, config, max_results: int = None) -> dict():
        """
        Config options:
            - css_selector (required): css selector to retrieve brut post identifiers
            - regex (required): regex used to filter brut content of css selector
        """

        css_selector = config.css_selector

        item_hrefs = []

        for item in self.driver.wait_and_find_elements(By.CSS_SELECTOR, css_selector):
            try:
                url = self.get_post_identifier(item, config)
                if url:
                    item_hrefs.append(url)

            except StaleElementReferenceException as e:
                logger.info("StaleElementReferenceException on get_urls_from_page")
                logger.info(str(e))
                continue

            except Exception as e:
                logger.info("Exception on get_urls_from_page")
                logger.info(str(e))
                continue

            if max_results and len(item_hrefs) >= max_results:
                break

        item_hrefs = set(item_hrefs)

        return dict.fromkeys(item_hrefs, None)

    def load_more_results(self, load_more_results_module, action_before_search_pages_browsing_module):
        logger.info("load_more_results")

        load_more_results_module_config = load_more_results_module
        load_more_results_module = getattr(loader_modules, load_more_results_module_config.name)
        load_more_results_module(
            selenium_driver=self,
            config=load_more_results_module_config,
            action_before_search_pages_browsing_module=action_before_search_pages_browsing_module,
        )
