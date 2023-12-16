from app import logger
from app.dao import PostDAO, OrganisationDAO
from app.models.enums import SEARCH_FRAMEWORKS, ScrapingType, DataSource
from app.service.send_post import send_posts
from app.service.save_poster import save_poster
from app.service.scrape_post_info import save_post, scrape_posts_with_selenium
from app.service.scrape_poster_info import scrape_poster_with_selenium
from app.service.search import (
    search_keywords_with_selenium,
    search_posters_with_selenium,
)
from app.helpers.utils import merge_dict_values
from .scraper import Scraper

post_DAO = PostDAO()
organisation_DAO = OrganisationDAO()


class MarketplaceScraper(Scraper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.batch_size = 2

        assert (
            self.organisation_name or self.scrape_search_results
        ), "If no organisation name is specified, 'scrape_search_results' should be activated to dispatch the results."

        assert (
            self.scraping_type != ScrapingType.POSTER_SEARCH
            or kwargs.get("domain_name") == "facebook.com"
            or self.config.search_pages_browsing_module.listing_container_css_selector
            or self.config.name == "api_selenium_framework"  # Required for scraping Poster Info
        ), "listing_container_css_selector is required for POSTER_SEARCH scraping type"

        if not self.source:
            self.source = DataSource.SPECIFIC_SCRAPER

        if self.scrape_search_results is None:
            if self.scraping_type != ScrapingType.POST_SCRAPE_FROM_LIST:
                if (
                    self.config.search_pages_browsing_module
                    and self.config.search_pages_browsing_module.listing_container_css_selector
                ):
                    self.scrape_search_results = True
                if self.config.search_pages_browsing_module.name == "search_only_browsing_module":
                    self.scrape_search_results = True
                    self.skip_detailed_post_scraping = True

        # Pass post url cleaning to picture method to verify variants' URL
        if (
            self.config.post_information_retriever_module
            and self.config.post_information_retriever_module.pictures_retriever_module
            and (
                self.config.post_information_retriever_module.pictures_retriever_module.post_url_cleaning_module is None
            )
        ):
            if (
                self.config.search_pages_browsing_module
                and self.config.search_pages_browsing_module.post_identifiers_retriever_module
                and self.config.search_pages_browsing_module.post_identifiers_retriever_module.post_url_cleaning_module
            ):
                self.config.post_information_retriever_module.pictures_retriever_module.post_url_cleaning_module = (
                    self.config.search_pages_browsing_module.post_identifiers_retriever_module.post_url_cleaning_module
                )

    def _search(self):
        """Run the right search framework"""

        logger.info("Start: search for listings")

        self.light_posts_to_scrape = {}

        if self.scraping_type == ScrapingType.POST_SCRAPE_FROM_LIST:
            self.light_posts_to_scrape = {post_id: dict() for post_id in self.post_urls}

        elif self.scraping_type in [ScrapingType.POST_SEARCH_COMPLETE]:
            if self.framework == SEARCH_FRAMEWORKS.SELENIUM.value:
                self.light_posts_to_scrape, self.total_count = search_keywords_with_selenium(
                    task_log_id=self.task_log_id,
                    domain_name=self.website.domain_name,
                    keywords=self.search_queries,
                    config=self.config,
                    max_results=self.max_posts_to_browse,
                    max_posts_to_discover=self.max_posts_to_discover,
                    scrape_search_results=self.scrape_search_results,
                    organisation_name=self.organisation_name,
                    search_urls=self.search_urls,
                    existing_platform_ids=self.existing_platform_ids,
                )

                logger.info(
                    f"Search returned {len(self.light_posts_to_scrape)} posts. Keywords contain {self.total_count} results in domain"
                )

            else:
                logger.info("Search framework Not Implemented Yet")

            logger.info(
                f"search completed with {len(self.light_posts_to_scrape)} posts. Keywords contain {self.total_count} results in domain"
            )

        elif self.scraping_type in [ScrapingType.POSTER_SEARCH] and self.scrape_poster_posts is True:
            if self.framework == SEARCH_FRAMEWORKS.SELENIUM.value:
                self.light_posts_to_scrape, self.total_count = search_posters_with_selenium(
                    task_log_id=self.task_log_id,
                    domain_name=self.website.domain_name,
                    config=self.config,
                    organisation_name=self.organisation_name,
                    poster_urls=self.poster_urls,
                    scrape_search_results=self.scrape_search_results,
                    max_results=self.max_posts_to_browse,
                    max_posts_to_discover=self.max_posts_to_discover,
                )

                logger.info(
                    f"Search returned {len(self.light_posts_to_scrape)} posts. Keywords contain {self.total_count} results in domain"
                )

            else:
                logger.info("Search framework Not Implemented Yet")

        logger.info(
            f"search completed with {len(self.light_posts_to_scrape)} posts. Keywords contain {self.total_count} results in domain"
        )

        # Update the task log
        self._update_task_log(
            body={
                "number_of_results_founds": len(self.light_posts_to_scrape),
                "light_posts_extraction_info": self._get_scraped_data_stats(list(self.light_posts_to_scrape.values())),
            }
        )

    def _save_search_results(self):
        for platform_id, post_data in self.light_posts_to_scrape.items():
            light_post_log = post_DAO.save_light_post_log(
                platform_id=platform_id,
                light_post=self.light_posts_to_scrape[platform_id],
                website_id=self.website.id,
                organisation_id=self.organisation and self.organisation.id,
                task_id=self.task_id,
            )
            post_data["light_post_log_id"] = light_post_log.id

            post_DAO.upsert_light_post(
                platform_id=platform_id,
                website_id=self.website.id,
                organisation_id=self.organisation and self.organisation.id,
            )

    def _filter_search_results(self):
        logger.info("Start: filter search results")

        self.posts_to_scrape = self.light_posts_to_scrape

        if not self.posts_to_scrape:
            return

        if not self.rescrape_existing_posts:
            # Remove previously scraped posts
            self.posts_to_scrape = post_DAO.filter_existing_posts(
                light_posts_to_scrape=self.posts_to_scrape,
                website_id=self.website.id,
                organisation_name=self.organisation_name,
            )
            logger.info(f"After removing old posts new count is {len(self.posts_to_scrape)} posts")
            # Update the task log
            self._update_task_log(body={"number_of_new_results_found": len(self.posts_to_scrape)})

        if self.skip_search_filter:
            return

        if not self.scrape_search_results:
            return

        # avoid importing unless fitlering is expected for memory reasons
        from app.service.filter.filter_search_results_marketplaces import filter_marketplace_search_results

        self.posts_to_scrape = filter_marketplace_search_results(
            self.posts_to_scrape,
            organisation=self.organisation,
            website=self.website,
            sample=self.sample,
        )

        self._update_task_log(body={"number_of_filtered_results_found": len(self.posts_to_scrape)})

    def _format_post_urls_to_scraped_posts(self, light_posts_to_scrape: dict):
        """Format Search Results From Identifier : {data} to {data}"""
        posts_data = [post_info for post_id, post_info in light_posts_to_scrape.items()]
        for post_data in posts_data:
            save_post(post=post_data, website=self.website, task_id=self.task_id)

        return posts_data

    def _scrape(self):
        logger.info("Start: scrape listings")

        if len(self.posts_to_scrape) > 0:
            if self.skip_detailed_post_scraping:
                self.scraped_posts = self._format_post_urls_to_scraped_posts(self.posts_to_scrape)
            else:
                logger.info(f"Scrape post list {len(self.posts_to_scrape)}")
                self.scraped_posts = scrape_posts_with_selenium(
                    website=self.website,
                    light_posts_to_scrape=self.posts_to_scrape,
                    task_id=self.task_id,
                    config=self.config,
                    upload_request_id=self.upload_request_id,
                    organisation_name=self.organisation_name,
                )

                logger.info(
                    f"Scraping returned {len(self.scraped_posts)} posts out of {len(self.posts_to_scrape)} posts"
                )

            self.number_of_results_founds += len(self.posts_to_scrape)
            self.number_of_complete_results_found += len(self.scraped_posts)
            self.post_extraction_info = merge_dict_values(
                self.post_extraction_info or {},
                self._get_scraped_data_stats(self.scraped_posts),
            )

        if len(self.poster_urls) > 0:
            logger.info(f"Scrape poster list {len(self.poster_urls)}")

            self.scraped_posters = scrape_poster_with_selenium(
                domain_name=self.website.domain_name,
                poster_urls=self.poster_urls,
                config=self.config,
                upload_request_id=self.upload_request_id,
                upload_account_identifier_url_mapping=self.upload_account_identifier_url_mapping,
            )

            logger.info(f"Scraping returned {len(self.scraped_posters)} posters out of {len(self.poster_urls)} posters")

            self.number_of_results_founds += len(self.poster_urls)
            self.number_of_complete_results_found += len(self.scraped_posters)
            self.poster_extraction_info = merge_dict_values(
                self.poster_extraction_info or {}, self._get_scraped_data_stats(self.scraped_posters)
            )

    def _save_and_send_posters(self):
        logger.info("Start: save & send posters")

        if not self.scraped_posters:
            return

        save_poster(
            posters=self.scraped_posters,
            domain_name=self.website.domain_name,
            send_to_counterfeit_platform=self.send_to_counterfeit_platform,
            accounts_batch=self.upload_accounts_batch,
            upload_request_id=self.upload_request_id,
            organisation_name=self.organisation_name,
        )

    def _filter_scraped_results(self):
        if self.skip_search_filter and self.organisation is not None:
            return

        # skip import unless needed
        from app.service.filter.filter_scraped_results_marketplaces import filter_marketplace_scraped_results

        self.scraped_posts = filter_marketplace_scraped_results(
            self.scraped_posts,
            organisation=self.organisation,
        )

    def _send(self):
        if not self.scraped_posts:
            return

        send_posts(
            posts=self.scraped_posts,
            website=self.website,
            send_to_counterfeit_platform=self.send_to_counterfeit_platform,
            search_queries=self.search_queries,
            upload_posts_batch=self.upload_posts_batch,
            upload_request_id=self.upload_request_id,
            post_identifier_url_mapping=self.post_identifier_url_mapping,
            source=self.source,
            override_save=self.override_save,
            post_tags=self.tags,
            task_id=self.task_id,
        )
