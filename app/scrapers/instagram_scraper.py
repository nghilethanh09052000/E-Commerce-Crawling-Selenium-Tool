from datetime import datetime, timezone

from app import logger
from app.helpers.utils import load_instagram_search_configs, merge_dict_values
from app.models.enums import ScrapingType
from app.service.filter.filter_scraped_results_ig import filter_ig_scraped_results, select_instagram_profiles
from app.service.filter.filter_search_results_ig import filter_ig_search_results
from app.service.send_post import create_or_update_instagram_posts
from app.service.save_poster import create_or_update_instagram_profiles
from app.service.scrape_post_info import scrape_instagram_posts, scrape_instagram_posts_from_usernames
from app.service.scrape_poster_info import scrape_instagram_profiles
from app.service.screenshot import take_instagram_post_screenshots, take_instagram_profile_screenshots
from app.service.search import instagram_hashtags_posts_search, radarly_search
from app.service.send import send_instagram_posts, send_instagram_profiles
from app.dao import PostDAO, OrganisationDAO
from automated_moderation.dataset import BasePost

from .scraper import Scraper

post_DAO = PostDAO()
organisation_DAO = OrganisationDAO()


class InstagramScraper(Scraper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.batch_size = 10

    def _check_variables_consistency(self) -> None:
        super()._check_variables_consistency()

        if self.scraping_type == ScrapingType.POST_SEARCH_RADARLY:
            if not self.search_queries:
                raise ValueError("Scraping type is POST_SEARCH_RADARLY -> search_queries must be set")

    def _search(self):
        """Search for listings to scrape (posts/profiles)"""

        self.light_posts_to_scrape = []

        if self.scraping_type == ScrapingType.POST_SEARCH_COMPLETE:
            instagram_search_configs = load_instagram_search_configs()
            hashtags = instagram_search_configs[self.organisation_name or "Commons"]["search_hashtags"]

            # Scrape the posts corresponding to the hashtags provided
            self.light_posts_to_scrape = instagram_hashtags_posts_search(
                hashtags,
                max_posts_to_browse=self.max_posts_to_browse,
                max_attempts=self.max_attempts,
            )

        elif self.scraping_type == ScrapingType.POST_SEARCH_RADARLY:
            self.light_posts_to_scrape = radarly_search(
                organisation_name=self.organisation_name,
                domain_name=self.website.domain_name,
                search_queries=self.search_queries,
                post_id_regex=self.config.post_identifier_regex,
                previous_run_time=self.previous_run_time,
            )

        elif self.scraping_type == ScrapingType.POSTER_SEARCH:
            if self.scrape_poster_posts:
                # Scrape the usernames corresponding to the account crawling parameters
                # to get the posts to scrape in the actual scraping phase
                # For consistency of the framework, also mark the scraped posters as posters to scrape

                scraped_posters = scrape_instagram_profiles(
                    self.usernames,
                    user_id_by_username=self.username_user_id_mapping,
                    concurrency=self.concurrency,
                    rescrape=self.rescrape_existing_profiles,
                    upload_request_id=self.upload_request_id,
                    upload_accounts_batch=self.upload_accounts_batch,
                    upload_account_identifier_url_mapping=self.upload_account_identifier_url_mapping,
                )

                if self.scrape_poster_posts:
                    # Scrape the profiles corresponding to the posts scraped
                    usernames = [profile["username"] for profile in scraped_posters.values()]

                    self.light_posts_to_scrape = scrape_instagram_posts_from_usernames(usernames=usernames)

        elif self.scraping_type == ScrapingType.POST_SCRAPE_FROM_LIST:
            self.light_posts_to_scrape = [BasePost(id=shortcode) for shortcode in self.post_urls]

        # Update the task log
        self._update_task_log(
            body={
                "number_of_results_founds": len(self.light_posts_to_scrape),
                "light_posts_extraction_info": self._get_scraped_data_stats(
                    [light_post_to_scrape.serialize for light_post_to_scrape in self.light_posts_to_scrape]
                ),
            }
        )

    def _filter_search_results(self):
        """Remove listing from search results that shouldn't be scraped"""

        if not self.light_posts_to_scrape or self.scraping_type == ScrapingType.POST_SCRAPE_FROM_LIST:
            self.posts_to_scrape = {post.id: post for post in self.light_posts_to_scrape}
            return

        new_light_posts = (
            post_DAO.get_unscraped_light_posts(self.light_posts_to_scrape, domain_name="instagram.com")
            if not self.rescrape_existing_posts
            else self.light_posts_to_scrape
        )
        logger.info(f"After removing known posts new count is {len(new_light_posts)} posts")
        self._update_task_log(body={"number_of_new_results_found": len(new_light_posts)})

        if self.skip_search_filter:
            self.posts_to_scrape = {post.id: post for post in new_light_posts}
            return

        self.posts_to_scrape = filter_ig_search_results(
            new_light_posts, organisation=self.organisation, sample=self.sample
        )
        logger.info(
            f"After removing irrelevant posts new count is {len(self.posts_to_scrape)} posts ({len(self.posts_to_scrape)/len(new_light_posts)*100:.2f}%)"
        )
        self._update_task_log(body={"number_of_filtered_results_found": len(self.posts_to_scrape)})

    def _scrape(self):
        """Scrape listing information"""

        # Get the resulting posts
        self.scraped_posts = (
            scrape_instagram_posts(
                self.posts_to_scrape,
                concurrency=self.concurrency,
                upload_request_id=self.upload_request_id,
                post_identifier_upload_id_mapping=self.post_identifier_upload_id_mapping,
            )
            if self.posts_to_scrape
            else {}
        )

        for post_details in self.scraped_posts.values():
            post_details["query_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

        if self.scraping_type == ScrapingType.POSTER_SEARCH:
            self.scraped_posters = scrape_instagram_profiles(
                self.usernames,
                user_id_by_username=self.username_user_id_mapping,
                concurrency=self.concurrency,
                rescrape=self.rescrape_existing_profiles,
                upload_request_id=self.upload_request_id,
                upload_accounts_batch=self.upload_accounts_batch,
                upload_account_identifier_url_mapping=self.upload_account_identifier_url_mapping,
            )

        elif self.scrape_profiles:
            # Scrape the profiles corresponding to the posts scraped
            profiles_to_scrape = list(set([post["owner"]["username"] for post in self.scraped_posts.values()]))

            self.scraped_posters = scrape_instagram_profiles(
                profiles_to_scrape,
                concurrency=self.concurrency,
                rescrape=self.rescrape_existing_profiles,
            )

        logger.info(
            f"{len(self.scraped_posts)} posts have been scraped and {len(self.scraped_posters)} profiles have been scraped"
        )

        # Update the task log
        self.number_of_results_founds += len(self.posts_to_scrape)
        self.number_of_complete_results_found += len(self.scraped_posts)

        self.post_extraction_info = merge_dict_values(
            self.post_extraction_info or {},
            self._get_scraped_data_stats([value for key, value in self.scraped_posts.items()]),
        )

        if self.scraped_posters:
            self.poster_extraction_info = merge_dict_values(
                self.poster_extraction_info or {},
                self._get_scraped_data_stats([value for key, value in self.scraped_posters.items()]),
            )

    def _save_posts(self):
        """Save & send the relevant scraped data"""

        logger.info("Start: save results")

        # When saving posts, they must be saved within an organisation so we use a neutral organisation if organisation_name is None
        organisation_name = self.organisation_name if self.organisation_name else "Commons"

        self.saved_posts = create_or_update_instagram_posts(self.scraped_posts, organisation_name, task_id=self.task_id)
        self.saved_posters = create_or_update_instagram_profiles(self.scraped_posters)

        logger.info(
            f"{len(self.saved_posts)} posts have been saved and {len(self.saved_posters)} profiles have been saved"
        )

    def _filter_scraped_results(self):
        """Filter scraped results to allocate source organisation or remove unecessary data"""

        self.profiles_to_send = select_instagram_profiles(
            scraped_posters=self.saved_posters,
        )

        self.posts_to_send = filter_ig_scraped_results(
            scraped_post_by_ids=self.saved_posts,
            organisation=self.organisation,
        )

        nb_distinct_selected_posts = len(set([post["shortcode"] for post in self.posts_to_send]))

        logger.info(
            f"{len(self.profiles_to_send)} profiles have been selected - {len(self.posts_to_send)} posts have been selected in total - {nb_distinct_selected_posts} distinct posts have been selected"
        )

        # Count the number of posts selected per brand
        organisation_posts_selected_mapping = dict()
        for post_to_send in self.posts_to_send:
            organisation_name = post_to_send["organisation_name"]
            organisation_posts_selected_mapping.setdefault(organisation_name, []).append(post_to_send)

        # Log the number of posts selected per brand
        for organisation_name, org_posts_to_send in organisation_posts_selected_mapping.items():
            logger.info(f"{len(org_posts_to_send)} posts have been selected for {organisation_name}")

            for post_to_send in org_posts_to_send:
                post_DAO.set_post_organisation(
                    platform_id=post_to_send["shortcode"],
                    organisation_name=organisation_name,
                    domain_name="instagram.com",
                )

    def _screenshot(self):
        """Take screenshots of the posts and profiles that we want to take screenshots of"""

        if self.screenshot_posts:
            take_instagram_post_screenshots(self.posts_to_send, self.scraped_posts)

        if self.screenshot_profiles:
            take_instagram_profile_screenshots(self.profiles_to_send, self.scraped_posters)

    def _send(self):
        """Send the posts and profiles of interest to the Counterfeit Platform"""
        if not self.send_to_counterfeit_platform:
            logger.info("Not sending to the Counterfeit Platform")
            return

        if self.posts_to_send:
            send_instagram_posts(
                self.posts_to_send,
                upload_posts_batch=self.upload_posts_batch,
                upload_request_id=self.upload_request_id,
                post_identifier_url_mapping=self.post_identifier_url_mapping,
                post_identifier_upload_id_mapping=self.post_identifier_upload_id_mapping,
            )

        if self.scrape_profiles and self.profiles_to_send:
            send_instagram_profiles(
                self.profiles_to_send,
                organisation_name=self.organisation_name,
                upload_accounts_batch=self.upload_accounts_batch,
                upload_request_id=self.upload_request_id,
                upload_account_identifier_url_mapping=self.upload_account_identifier_url_mapping,
            )
