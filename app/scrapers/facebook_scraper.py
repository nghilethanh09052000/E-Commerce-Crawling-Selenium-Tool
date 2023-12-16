from typing import List
from datetime import datetime
import random

from app import logger
from app.helpers.utils import merge_dict_values
from app.models.enums import ScrapingType, DataSource
from app.service.data365 import data365_post_search, data365_poster_search, data365_post_scraping
from automated_moderation.dataset import BasePost
from app.service.send_post import send_posts
from app.service.send import send_profile_insertion_task
from .scraper import Scraper
from app.dao import PostDAO, WebsiteDAO, PosterDAO
from app.service.filter.filter_search_results_ig import filter_ig_search_results

post_DAO = PostDAO()
website_DAO = WebsiteDAO()
poster_DAO = PosterDAO()


class FacebookScraper(Scraper):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.batch_size = 5
        self.scrape_search_results = True
        self.source = DataSource.SPECIFIC_SCRAPER

    def _check_variables_consistency(self) -> None:
        super()._check_variables_consistency()

        if self.scraping_type == ScrapingType.POST_SEARCH_RADARLY:
            if not self.search_queries:
                raise ValueError("Scraping type is POST_SEARCH_RADARLY -> search_queries must be set")

    def _search(self):
        """Search for listings to scrape (posts/profiles)"""

        logger.info("Start: Data365 search")

        random.shuffle(self.search_queries)

        self.light_posts_to_scrape: List[BasePost] = data365_post_search(
            organisation_name=self.organisation_name,
            search_queries=self.search_queries,
            max_posts_to_browse=self.max_posts_to_browse,
        )

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
        # FIXME: duplicated from instagram_scraper.py

        if not self.light_posts_to_scrape or self.scraping_type == ScrapingType.POST_SCRAPE_FROM_LIST:
            self.posts_to_scrape = {post.id: post for post in self.light_posts_to_scrape}
            return

        new_light_posts = (
            post_DAO.get_unscraped_light_posts(self.light_posts_to_scrape, domain_name="facebook.com")
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
        """For facebook, we don't do post scraping yet so we just return the search results"""

        self.scraped_posts = [
            {
                "id": post.id,
                "url": post.url,
                "scraping_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": post.description,
                "vendor": post.poster.name,
                "poster_website_identifier": post.poster.website_identifier,
                "poster_url": post.poster.url,
                "pictures": [{"picture_url": image.url, "s3_url": image.s3_url} for image in post.images],
                "title": post.title,
                "price": None,
                "posting_time": datetime.strptime(post.created_at, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M:%S"),
                "archive_link": post.archive_link,
            }
            for post in data365_post_scraping(
                post_ids=self.posts_to_scrape.keys(), organisation_name=self.organisation_name
            )
        ]

        if self.scraped_posts:
            self.number_of_results_founds += len(self.posts_to_scrape)
            self.number_of_complete_results_found += len(self.scraped_posts)
            self.post_extraction_info = merge_dict_values(
                self.post_extraction_info or {},
                self._get_scraped_data_stats(self.scraped_posts),
            )

        posters = data365_poster_search(
            poster_ids=list(set([post["poster_website_identifier"] for post in self.scraped_posts]))
        )
        self.scraped_posters = [
            {
                "name": poster.name,
                "description": poster.description,
                "url": poster.url,
                "profile_pic_url": poster.profile_pic_url,
                "archive_link": poster.archive_link,
                "followers_count": poster.followers_count or 0,
                "poster_website_identifier": poster.id,
            }
            for poster in posters
        ]

        if self.scraped_posters:
            self.poster_extraction_info = merge_dict_values(
                self.poster_extraction_info or {}, self._get_scraped_data_stats(self.scraped_posters)
            )

    def _save_and_send(self):
        facebook = website_DAO.get("facebook.com")

        # Save
        for post in self.scraped_posts:
            post_DAO.upsert_facebook_post(post_json=post, organisation=self.organisation, task_id=self.task_id)

        for poster in self.scraped_posters:
            poster_DAO.upsert_profile(
                username=poster["name"],
                website=facebook,
                description=poster["description"],
                url=poster["url"],
                profile_pic_url=poster["profile_pic_url"],
                posts_count=None,
                followers_count=poster["followers_count"],
                poster_website_identifier=poster["poster_website_identifier"],
            )

        # Add the organisation name to each post
        for post in self.scraped_posts:
            post["organisation_names"] = [self.organisation_name]

        # Send
        logger.info("Start: save results")

        if self.scraped_posts:
            send_posts(
                posts=self.scraped_posts,
                domain_name=self.website.domain_name,
                send_to_counterfeit_platform=self.send_to_counterfeit_platform,
                source=self.source,
                website=self.website,
                override_save=self.override_save,
                post_tags=self.tags,
            )

        for poster in self.scraped_posters:
            send_profile_insertion_task(poster, organisation_name=self.organisation_name)
