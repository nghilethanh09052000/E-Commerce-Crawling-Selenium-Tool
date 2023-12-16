from app import logger
from app.dao import PostDAO
from app.models.enums import ScrapingType
from app.service.api_scraping.scrape_post import scrape_post_with_api
from app.service.api_scraping.search import search_keywords_with_api, search_images_with_api
from app.helpers.utils import merge_dict_values
from .marketplace_scraper import MarketplaceScraper

post_DAO = PostDAO()


class APIScraper(MarketplaceScraper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.batch_size = 10
        self.scrape_search_results = True

        if (
            self.config
            and self.config.post_information_retriever_module
            and self.config.post_information_retriever_module.use_light_post_info_only is True
        ):
            self.skip_detailed_post_scraping = True

    def _search(self):
        """Run the right search framework"""

        logger.info("Start: search for listings")

        self.light_posts_to_scrape = {}

        if self.scraping_type == ScrapingType.POST_SCRAPE_FROM_LIST:
            self.light_posts_to_scrape = {post_id: dict() for post_id in self.post_urls}

        elif self.scraping_type in [ScrapingType.POST_SEARCH_COMPLETE]:
            self.light_posts_to_scrape, self.total_count = search_keywords_with_api(
                domain_name=self.website.domain_name,
                keywords=self.search_queries,
                config=self.config,
                max_results=self.max_posts_to_browse,
                organisation_name=self.organisation_name,
                search_urls=self.search_urls,
                existing_platform_ids=self.existing_platform_ids,
                max_posts_to_discover=self.max_posts_to_discover,
                task_log_id=self.task_log_id,
            )
        elif self.scraping_type in [ScrapingType.POST_IMAGE_SEARCH_COMPLETE]:
            self.light_posts_to_scrape, self.total_count = search_images_with_api(
                domain_name=self.website.domain_name,
                search_image_urls=self.search_image_urls,
                config=self.config,
                max_results=self.max_posts_to_browse,
                organisation_name=self.organisation_name,
                search_urls=self.search_urls,
                existing_platform_ids=self.existing_platform_ids,
                max_posts_to_discover=self.max_posts_to_discover,
                task_log_id=self.task_log_id,
            )
        # elif self.scraping_type in [ScrapingType.POSTER_SEARCH] and self.scrape_poster_posts is True:
        #
        #     self.light_posts_to_scrape, self.total_count = search_posters_with_selenium(
        #         domain_name=self.website.domain_name,
        #         config=self.config,
        #         organisation_name=self.organisation_name,
        #         poster_urls=self.poster_urls,
        #         scrape_search_results=self.scrape_search_results,
        #         max_results=self.max_posts_to_browse,
        #     )

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

    def _scrape(self):
        logger.info("Start: scrape listings")

        if len(self.posts_to_scrape) > 0:
            if self.skip_detailed_post_scraping:
                self.scraped_posts = self._format_post_urls_to_scraped_posts(self.posts_to_scrape)
            else:
                logger.info(f"Scrape post list {len(self.posts_to_scrape)}")
                self.scraped_posts = scrape_post_with_api(
                    website=self.website,
                    light_posts_to_scrape=self.posts_to_scrape,
                    config=self.config,
                    upload_request_id=self.upload_request_id,
                    post_identifier_upload_id_mapping=self.post_identifier_upload_id_mapping,
                    organisation_name=self.organisation_name,
                    task_id=self.task_id,
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
