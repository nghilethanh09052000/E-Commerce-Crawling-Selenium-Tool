from app import logger, sentry_sdk
from datetime import datetime
from typing import List, Optional
from app.dao import TaskLogDAO, WebsiteDAO, OrganisationDAO
from app.dao.post import PostDAO
from app.models.enums import ScrapingType, DataSource
from app.models.marshmallow.config import ScrapeSchema
from app.settings import DEFAULT_MAX_POSTS_TO_BROWSE
from app.configs.utils import load_config

task_log_DAO = TaskLogDAO()
website_DAO = WebsiteDAO()
organisation_DAO = OrganisationDAO()
post_DAO = PostDAO()


class Scraper:
    def __init__(
        self,
        domain_name: str,
        scraping_type: ScrapingType = None,
        source: DataSource = None,
        config_file: str = None,
        organisation_name: str = None,
        search_queries: List[str] = None,
        search_image_urls: List[str] = None,
        search_urls: List[str] = None,
        poster_urls: dict = {},
        post_urls: dict = {},
        upload_request_id: str = None,
        post_identifier_upload_id_mapping: dict = {},
        post_identifier_url_mapping: dict = {},
        upload_posts_batch: dict = {},
        send_to_counterfeit_platform: bool = True,
        rescrape_existing_posts=False,
        scrape_poster_posts: bool = False,
        task_id: int = None,
        total_count: int = 0,
        scraped_posts: list = [],
        enable_logging: bool = True,
        max_posts_to_browse: int = None,
        scrape_search_results: bool = None,
        skip_detailed_post_scraping: bool = False,
        usernames: list = [],
        scrape_profiles: bool = True,
        rescrape_existing_profiles: bool = False,
        screenshot_posts: bool = True,
        screenshot_profiles: bool = True,
        skip_search_filter: bool = True,
        concurrency: int = 8,
        tags: List[str] = [],
        posts_to_send_per_hashtag: Optional[int] = None,
        username_user_id_mapping: dict = dict(),
        upload_accounts_batch=[],
        upload_account_identifier_url_mapping: dict = dict(),
        scraped_posters: dict = dict(),
        posts_to_send: list = [],
        profiles_to_send: dict = dict(),
        saved_posts: dict = dict(),
        saved_posters: dict = dict(),
        previous_run_time: datetime = None,
        max_attempts: Optional[int] = 3,
        filtering_threshold: Optional[float] = None,
        override_save: bool = False,
        sample: bool = False,
        max_posts_to_discover: int = None,
        **kwargs,
    ) -> None:
        # ===================================
        # Parameters common to every use case
        # ===================================
        self.website = website_DAO.get(domain_name=domain_name)
        self.scraping_type = scraping_type
        self.source = source
        self.config_file = config_file if config_file else domain_name
        self.organisation_name = organisation_name
        self.search_queries = None if not search_queries else list(search_queries)
        self.search_image_urls = None if not search_image_urls else list(search_image_urls)
        self.send_to_counterfeit_platform = send_to_counterfeit_platform
        self.scrape_poster_posts = scrape_poster_posts
        self.scrape_profiles = scrape_profiles
        self.rescrape_existing_posts = rescrape_existing_posts
        self.rescrape_existing_profiles = rescrape_existing_profiles
        self.screenshot_posts = screenshot_posts
        self.screenshot_profiles = screenshot_profiles
        self.task_id = task_id
        self.scraped_posts = scraped_posts
        self.scraped_posters = scraped_posters
        self.framework = None
        self.enable_logging = enable_logging
        self.override_save = override_save
        self.tags = tags
        self.post_urls = post_urls
        self.skip_search_filter = skip_search_filter
        self.sample = sample  # Whether or not to take a sample of the searched posts for filtering monitoring

        self.organisation = (
            organisation_DAO.get(organisation_name=self.organisation_name) if self.organisation_name else None
        )

        # =====================================================
        # Parameters useful for the handling of upload requests
        # =====================================================
        self.upload_request_id = (
            upload_request_id  # useful to set the URL upload status if the scraping of an account fails
        )
        self.post_identifier_upload_id_mapping = post_identifier_upload_id_mapping
        self.post_identifier_url_mapping = post_identifier_url_mapping
        self.upload_posts_batch = upload_posts_batch  # batch of posts provided when handling automated uploads of posts
        self.upload_accounts_batch = (
            upload_accounts_batch  # useful to get the tags, label and upload_id to send for insertion
        )
        self.upload_account_identifier_url_mapping = (
            upload_account_identifier_url_mapping  # useful to send the original URL to the Insertion Worker
        )

        # ==============================================
        # Parameters specific to the Marketplace Scraper
        # ==============================================
        self.poster_urls = poster_urls
        self.posts_to_scrape = None
        self.total_count = total_count
        self.scrape_search_results = scrape_search_results
        self.skip_detailed_post_scraping = skip_detailed_post_scraping
        self.search_urls = search_urls  # used to be included in search query search
        self.existing_platform_ids = set()

        # ===============================================
        # Parameters specific to the Social Media Scraper
        # ===============================================
        self.usernames = list(set(usernames))
        self.concurrency = concurrency

        self.posts_to_send_per_hashtag = posts_to_send_per_hashtag
        self.username_user_id_mapping = (
            username_user_id_mapping  # useful to scrape profiles using their user ID instead of username
        )
        self.posts_to_send = posts_to_send
        self.saved_posts = saved_posts
        self.profiles_to_send = profiles_to_send
        self.saved_posters = saved_posters
        self.previous_run_time = previous_run_time
        self.max_attempts = max_attempts
        self.filtering_threshold = filtering_threshold

        # =========================================
        # Enforce some constraints on the arguments
        # =========================================
        self._check_variables_consistency()

        # =========================================
        # Load Config File
        # =========================================
        self.config = self._load_config(self.config_file)
        self.max_posts_to_browse = self._get_max_posts_to_browse(max_posts_to_browse)
        self.max_posts_to_discover = max_posts_to_discover if max_posts_to_discover else self.max_posts_to_browse * 3

        # =========================================
        # Initiate Logging
        # =========================================
        self.task_log_id = self._get_task_log_id()
        # number of results to found to scrape
        self.number_of_results_founds = 0
        # number of results scraped correctly
        self.number_of_complete_results_found = 0
        self.post_extraction_info = None
        self.poster_extraction_info = None

    def _get_max_posts_to_browse(self, max_posts_to_browse):

        if max_posts_to_browse:
            value_to_set = max_posts_to_browse

        elif self.config.search_pages_browsing_module and self.config.search_pages_browsing_module.max_posts_to_browse:
            value_to_set = self.config.search_pages_browsing_module.max_posts_to_browse

        elif DEFAULT_MAX_POSTS_TO_BROWSE is not None:
            value_to_set = DEFAULT_MAX_POSTS_TO_BROWSE

        else:
            value_to_set = 100

        return value_to_set

    def _as_dict(self):
        return {
            "scraping_type": str(self.scraping_type),
            "domain_name": self.website.domain_name,
            "organisation_name": self.organisation_name,
            "send_to_counterfeit_platform": self.send_to_counterfeit_platform,
            "search_queries": self.search_queries,
            "search_image_urls": self.search_image_urls,
        }

    def _load_config(self, config_file) -> ScrapeSchema:
        """load configuration file and framework to use"""

        config = load_config(config_file)
        self.framework = config.name

        return config

    def run(self) -> bool:
        """Run the Scraper"""

        # Search for posts and/or profiles if needed
        self._get_existing_db_platform_ids()
        self._search()
        self._save_search_results()

        # Filter the posts to retrieve using AI model
        self._filter_search_results()

        # Functions related to scraping the listing after search

        if self.batch_size > 0:
            posts_to_scrape = self.posts_to_scrape if self.posts_to_scrape else {}

            if self.usernames:
                posters_to_scrape = {username: {} for username in self.usernames}
            elif self.poster_urls:
                posters_to_scrape = self.poster_urls
            else:
                posters_to_scrape = {}

            posts_to_scrape_keys = list(posts_to_scrape.keys())

            number_of_batches = len(posts_to_scrape_keys) // self.batch_size + 1
            for batch_index in range(0, len(posts_to_scrape_keys), self.batch_size):
                batch_number = batch_index // self.batch_size + 1

                logger.info(f"Working with Post dispatching Batch No {batch_number}/{number_of_batches}")

                try:
                    batch_keys = posts_to_scrape_keys[batch_index : batch_index + self.batch_size]

                    self.posts_to_scrape = {k: posts_to_scrape[k] for k in batch_keys}
                    self.poster_urls = {}
                    self.usernames = []

                    self._scrape_listings()

                except Exception as e:
                    logger.error(f"Error in post dispatching Batch No {batch_number} {e}")
                    sentry_sdk.capture_exception(e)

            posters_to_scrape_keys = list(posters_to_scrape.keys())

            for batch_index in range(0, len(posters_to_scrape_keys), self.batch_size):
                batch_number = batch_index // self.batch_size

                logger.info(f"Working with poster dispatching Batch No {batch_number}")

                try:
                    batch_keys = posters_to_scrape_keys[batch_index : batch_index + self.batch_size]

                    self.posts_to_scrape = {}

                    # Set both the poster URLs (for marketplace scraping) and the usernames (for social media scraping)
                    self.poster_urls = {k: posters_to_scrape[k] for k in batch_keys}
                    self.usernames = [k for k in batch_keys]

                    self._scrape_listings()

                except Exception as e:
                    logger.error(f"Error in poster dispatching Batch No {batch_number} {repr(e)}")
                    sentry_sdk.capture_exception(e)

        else:
            self._scrape_listings()

        # Update Log
        self._update_log()

        self._update_task_log(body={"end_date_time": datetime.now()})

        return self.light_posts_to_scrape, self.scraped_posts, self.scraped_posters

    def _scrape_listings(self) -> bool:
        """Run the functions related to post scraping"""

        # Scrape the posts and profiles that we want to retrieve
        self._scrape()

        # Save in database the posts and profiles scraped
        self._save_and_send_posters()
        self._save_posts()

        # Select the posts and profiles that we want to send to the Counterfeit Platform
        self._filter_scraped_results()

        # Take screenshots of the posts and profiles that we want to take screenshots of
        self._screenshot()

        # Save in database the posts and profiles scraped and send to the Counterfeit Platform at the same time
        self._save_and_send()

        # Send the posts and profiles of interest to the Counterfeit Platform
        self._send()

        # return the scraped data
        return True

    def _get_existing_db_platform_ids(self):
        """Get latest scraped posts prior to scraping"""
        if not self.rescrape_existing_posts:
            # get latest scraped platform ids
            self.existing_platform_ids = post_DAO.get_latest_platform_ids(
                organisation_id=self.organisation and self.organisation.id, website_id=self.website.id
            )

    def _search(self):
        """Search for listings to scrape"""
        pass

    def _save_search_results(self):
        """Save search results"""
        pass

    def _filter_search_results(self):
        """Remove listing from search results that shouldn't be scraped"""
        pass

    def _scrape(self):
        """Scrape listing information"""
        pass

    def _filter_scraped_results(self):
        """Filter scraped results to allocate source organisation or remove unecessary data"""
        pass

    def _screenshot(self):
        """Take screenshots of the posts and profiles that we want to take screenshots of"""
        pass

    def _save_posts(self):
        """Save & send the relevant scraped data"""
        pass

    def _save_and_send_posters(self):
        """Save & send the relevant scraped data"""
        pass

    def _get_task_log_id(self):
        if self.enable_logging:
            return task_log_DAO.create(
                name=self.scraping_type.name,
                task_id=self.task_id,
                website_id=None if self.website is None else self.website.id,
                payload=self._as_dict(),
            ).id

        return None

    def _update_task_log(self, body):
        if self.task_log_id:
            task_log_DAO.update(task_log_id=self.task_log_id, body=body)

    def _get_scraped_data_stats(self, scraped_data):
        """Get Statistics on how much data was scraped from each field"""

        if len(scraped_data) > 0:
            # Remove default keys and get keys of all fields on scraping
            post_keys = [
                key
                for key in scraped_data[0].keys()
                if key
                not in (
                    "skip_filter_scraped_results",
                    "translated_description",
                    "valid_organisations",
                    "is_desc_counterfeit",
                    "source_language",
                    "organisation",
                    "risk_score",
                    "label_name",
                    "hashtags," "created_at," "features",
                    "category",
                    "weight",
                    "organisation_name",
                    "scraping_time",
                    "id",
                    "light_post_payload",
                )
            ]

            data = {}
            for entry in post_keys:
                data[f"{entry}s_found"] = len(
                    [
                        post
                        for post in scraped_data
                        if (
                            post[entry] is not None
                            and len(str(post[entry])) > 1
                            and (type(post[entry]) != list or len(post[entry]) > 0)
                        )
                    ]
                )

            return data

        return {}

    def _check_variables_consistency(self):
        pass

    def _send(self):
        pass

    def _save_and_send(self):
        pass

    def _update_log(self):
        # Update the task log
        self._update_task_log(
            body={
                "number_of_complete_results_found": self.number_of_complete_results_found,
                "post_extraction_info": self.post_extraction_info,
                "poster_extraction_info": self.poster_extraction_info,
            }
        )
