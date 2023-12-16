import calendar
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy import desc, distinct
from sqlalchemy import orm
from sqlalchemy.exc import IntegrityError

from app import logger, sentry_sdk
from app.models import Organisation, Post, Session, Website, LightPostLog, ScrapedPostLog
from automated_moderation.dataset import BasePost
from app.models.enums import ScrapingStatus

from .organisation import OrganisationDAO
from .utils import safe_bulk_insert_mappings, safe_bulk_update_mappings
from .website import WebsiteDAO

organisation_dao = OrganisationDAO()
website_dao = WebsiteDAO()


class PostDAO:
    def _get(self, session: orm.Session, platform_id: str, website_id: int, organisation_id: int) -> Optional[Post]:
        return (
            session.query(Post)
            .filter(
                Post.platform_id == platform_id,
                Post.website_id == website_id,
                Post.organisation_id == organisation_id,
            )
            .one_or_none()
        )

    def get_latest_platform_ids(self, website_id: int, organisation_id: int = None, limit=10000) -> Optional[Post]:
        """Returns latest scraped platfrorm ids"""
        with Session() as session:
            query = session.query(Post.platform_id).filter(
                Post.website_id == website_id,
                Post.scraping_status.in_([ScrapingStatus.FILTERED_OUT, ScrapingStatus.SENT]),
            )
            if organisation_id:
                query = query.filter(Post.organisation_id == organisation_id)
            return set([post[0] for post in query.order_by(desc(Post.scraping_time)).limit(limit).all()])

    def save_light_post_log(
        self, light_post: dict, platform_id: str, website_id: int, organisation_id: Optional[int], task_id: int
    ) -> LightPostLog:
        with Session() as session:
            light_post_log = LightPostLog(
                platform_id=platform_id,
                organisation_id=organisation_id,
                website_id=website_id,
                task_id=task_id,
                light_post_payload=light_post,
            )
            session.add(light_post_log)
            session.commit()

        return light_post_log

    def upsert_light_post(self, platform_id: str, website_id: int, organisation_id: int) -> Post:
        with Session() as session:
            if post := self._get(
                session, platform_id=platform_id, website_id=website_id, organisation_id=organisation_id
            ):
                return post

            post = Post(
                platform_id=platform_id,
                website_id=website_id,
                organisation_id=organisation_id,
                scraping_status=ScrapingStatus.SEARCHED,
            )
            session.add(post)
            session.commit()

        return post

    def save_scraped_post(self, post_data: dict, organisation_id: int, website_id: int, task_id: int):
        with Session() as session:
            scraped_post_log = ScrapedPostLog(
                platform_id=post_data["id"],
                organisation_id=organisation_id,
                website_id=website_id,
                task_id=task_id,
                post_payload=post_data,
            )
            session.add(scraped_post_log)
            session.commit()

    def update_post(self, post_data: dict, organisation_id: int, website_id: int, task_id: int):
        try:
            scraping_time = datetime.strptime(post_data["scraping_time"], "%Y-%m-%d-%H:%M:%S")
        except Exception as ex:
            logger.info("Error Parsing Scraping Time Resolve to default scraping time")
            scraping_time = datetime.now(timezone.utc)
            sentry_sdk.capture_message(ex)

        with Session() as session:
            post = self._get(
                session, platform_id=post_data["id"], website_id=website_id, organisation_id=organisation_id
            )

            if not post:
                logger.error(
                    f"Post with platform id {post_data['id']}, website id {website_id} and organisation id {organisation_id} not found"
                )
                return

            post.organisation_id = organisation_id
            post.website_id = website_id
            post.task_id = task_id
            post.scraping_time = scraping_time
            post.platform_id = post_data["id"]
            post.url = post_data["url"]
            post.title = post_data["title"]
            post.description = post_data["description"]
            post.price = post_data["price"]
            post.pictures = [picture["picture_url"] for picture in post_data["pictures"]]
            post.stock_count = post_data.get("stock_count")
            post.vendor = post_data["vendor"]
            post.videos = post_data.get("videos")
            post.archive_link = post_data.get("archive_link")
            post.poster_link = post_data.get("poster_link")
            post.location = post_data.get("location")
            post.ships_from = post_data.get("ships_from")
            post.ships_to = post_data.get("ships_to")
            post.posting_time = post_data.get("posting_time")
            post.risk_score = post_data.get("risk_score")
            post.alternate_links = post_data.get("alternate_links")

            if post.scraping_status != ScrapingStatus.SENT:
                post.scraping_status = ScrapingStatus.SCRAPED

            session.commit()

    def filter_existing_posts(self, light_posts_to_scrape: dict, website_id: int, organisation_name=None):
        with Session() as session:
            query = session.query(Post.platform_id).filter(
                Post.website_id == website_id,
                Post.platform_id.in_(light_posts_to_scrape.keys()),
                Post.scraping_status.in_([ScrapingStatus.FILTERED_OUT, ScrapingStatus.SENT]),
            )

            if organisation_name:
                query = query.join(Organisation, Organisation.id == Post.organisation_id).filter(
                    Organisation.name == organisation_name
                )

            existing_posts = set([q[0] for q in query.all()])

            if len(existing_posts) < 1:
                return light_posts_to_scrape

            return {
                post_url: post_data
                for post_url, post_data in light_posts_to_scrape.items()
                if post_url not in existing_posts
            }

    def add_filter_logs(self, light_post_log_id: int, filter_post_payload: dict, risk_score: int):
        with Session() as session:
            light_post_log = session.query(LightPostLog).filter(LightPostLog.id == light_post_log_id).one_or_none()

            if not light_post_log:
                logger.error(f"Light post log with id {light_post_log_id} not found")
                return

            light_post_log.filter_post_payload = filter_post_payload
            light_post_log.risk_score = risk_score
            session.commit()

    def count_posts_sent_this_month(self, organisation_id):
        current_month = datetime.today().month
        current_year = datetime.today().year
        monthrange = calendar.monthrange(current_year, current_month)

        with Session() as session:
            return (
                session.query(Post)
                .filter(Post.organisation_id == organisation_id)
                .filter(Post.sent_to_counterfeit_platform.is_(True))
                .filter(datetime(current_year, current_month, 1) < Post.scraping_time)
                .filter(Post.scraping_time < datetime(current_year, current_month, monthrange[1], 23, 59, 59))
                .count()
            )

    def bulk_save_posts_in_db(self, posts):
        return safe_bulk_insert_mappings(mapper=Post, mappings=posts)

    def bulk_update_posts_in_db(self, posts):
        return safe_bulk_update_mappings(mapper=Post, mappings=posts)

    def get_unscraped_light_posts(self, light_posts: List[BasePost], domain_name: str) -> List[BasePost]:
        website = website_dao.get(domain_name)
        shortcodes = [post.id for post in light_posts]

        with Session() as session:
            # Select all the shortcodes which have previously been scraped and saved to the database
            scraped_shortcodes_query = session.query(distinct(Post.platform_id)).filter(
                Post.website_id == website.id,
                Post.platform_id.in_(shortcodes),
                Post.scraping_status.in_([ScrapingStatus.FILTERED_OUT, ScrapingStatus.SENT]),
            )

            scraped_shortcodes = [row[0] for row in scraped_shortcodes_query.all()]
        unscraped_posts = [post for post in light_posts if post.id not in scraped_shortcodes]

        return unscraped_posts

    def upsert_facebook_post(self, post_json, organisation, task_id):
        facebook = website_dao.get("facebook.com")

        with Session() as session:
            try:
                post = Post(
                    organisation=organisation,
                    website=facebook,
                    scraping_time=post_json["scraping_time"],
                    platform_id=post_json["id"],
                    url=post_json["url"],
                    posting_time=post_json["posting_time"],
                    description=post_json["description"],
                    pictures=[picture["s3_url"] for picture in post_json["pictures"]],
                    vendor=post_json["vendor"],
                    poster_link=post_json["poster_url"],
                    poster_website_identifier=post_json["poster_website_identifier"],
                    risk_score=post_json.get("risk_score"),
                    light_post_payload=post_json.get("light_post_payload"),
                    task_id=task_id,
                )
                session.add(post)
                session.commit()

            except IntegrityError:
                session.rollback()

                post: Post = (
                    session.query(Post)
                    .filter_by(
                        organisation=organisation,
                        website=facebook,
                        platform_id=post_json["id"],
                    )
                    .one()
                )

        return post

    def create_or_update_instagram_post(self, post_json, organisation, scraping_time, task_id):
        instagram = website_dao.get("instagram.com")

        url = f"https://www.instagram.com/p/{post_json['shortcode']}"
        vendor = post_json["owner"].get("username")
        poster_website_identifier = post_json["owner"].get("id")
        pictures = post_json["pictures"]
        description = post_json["caption"]

        with Session() as session:
            try:
                post = Post(
                    organisation=organisation,
                    website=instagram,
                    scraping_time=scraping_time,
                    platform_id=post_json["shortcode"],
                    url=url,
                    posting_time=datetime.strptime(post_json["publication_datetime"], "%Y-%m-%d %H:%M:%S"),
                    description=description,
                    pictures=pictures,
                    vendor=vendor,
                    poster_website_identifier=poster_website_identifier,
                    risk_score=post_json.get("risk_score"),
                    light_post_payload=post_json.get("light_post_payload"),
                    task_id=task_id,
                )
                session.add(post)
                session.commit()

            except IntegrityError:
                session.rollback()

                post: Post = (
                    session.query(Post)
                    .filter_by(
                        organisation=organisation,
                        website=instagram,
                        platform_id=post_json["shortcode"],
                    )
                    .one()
                )

                # Update
                post.scraping_time = scraping_time
                post.url = url
                post.posting_time = datetime.strptime(post_json["publication_datetime"], "%Y-%m-%d %H:%M:%S")
                post.description = description
                post.pictures = pictures
                post.vendor = vendor
                post.poster_website_identifier = poster_website_identifier
                post.risk_score = post_json.get("risk_score")
                post.light_post_payload = post_json.get("light_post_payload")
                session.commit()

            return post

    def set_post_archive_link(self, post_object: Post, archive_link: str):
        post_object.archive_link = archive_link

        with Session() as session:
            post = session.query(Post).get(post_object.id)
            post.archive_link = archive_link
            session.commit()

        return post

    def get_date_of_last_post_crawled(self, organisation_name, domain_name):
        """Get the scraping time of the last post which was scraped for a given organisation on a given website"""

        with Session() as session:
            last_post = (
                session.query(Post.scraping_time)
                .join(Organisation, Organisation.id == Post.organisation_id)
                .join(Website, Website.id == Post.website_id)
                .filter(Organisation.name == organisation_name)
                .filter(Website.name == domain_name)
                .order_by(desc(Post.scraping_time))
                .first()
            )

        if last_post:
            return last_post[0]
        else:
            return datetime(1900, 1, 1)

    def select_scraped_posts(self, domain_name, organisation_name=None):
        """Return the identifiers of posts posts which are already stored in database for these organisation and website"""

        with Session() as session:
            posts_in_database_query = (
                session.query(Post.platform_id)
                .join(Website, Website.id == Post.website_id)
                .filter(Website.name == domain_name)
            )

            if organisation_name:
                posts_in_database_query = posts_in_database_query.join(
                    Organisation, Organisation.id == Post.organisation_id
                ).filter(Organisation.name == organisation_name)

            posts_in_database = [row[0] for row in posts_in_database_query]

        return posts_in_database

    def select_not_scraped_and_unique_posts(self, posts, organisation_name, domain_name):
        """We filter the array posts to keep those which were not already in the database and without duplicates"""

        scraped_posts_ids = self.select_scraped_posts(organisation_name=organisation_name, domain_name=domain_name)

        filtered_posts = []
        filtered_posts_ids = []

        for post in posts:
            post_id = post.id
            if post_id not in scraped_posts_ids and post_id not in filtered_posts_ids:
                filtered_posts.append(post)
                filtered_posts_ids.append(post_id)

        return filtered_posts

    def get_id(self, website_id: int, platform_id: str, organisation_id: int) -> Optional[int]:
        with Session() as session:
            post = self._get(session, platform_id=platform_id, website_id=website_id, organisation_id=organisation_id)

        return post.id if post else None

    def set_post_organisation(self, platform_id: str, organisation_name: str, domain_name: int):
        with Session() as session:
            post: Post = (
                session.query(Post)
                .join(Organisation, Organisation.id == Post.organisation_id)
                .join(Website, Website.id == Post.website_id)
                .filter(
                    Post.platform_id == platform_id,
                    Website.domain_name == domain_name,
                    Organisation.name == organisation_name,
                )
                .one_or_none()
            )

            if post:
                return

            post: Post = (
                session.query(Post)
                .join(Organisation, Organisation.id == Post.organisation_id)
                .join(Website, Website.id == Post.website_id)
                .filter(
                    Post.platform_id == platform_id,
                    Website.domain_name == domain_name,
                    Organisation.name == "Commons",
                )
                .one_or_none()
            )

            if not post:
                sentry_sdk.capture_message(
                    f"Post with platform_id {platform_id} not found in database for organisation {organisation_name} and domain {domain_name}",
                    level="warning",
                )
                return

            organisation = session.query(Organisation).filter_by(name=organisation_name).one()

            post.organisation = organisation
            session.commit()

    def set_post_as_sent(self, platform_id: str, organisation_name: str, domain_name: int):
        with Session() as session:
            post: Post = (
                session.query(Post)
                .join(Organisation, Organisation.id == Post.organisation_id)
                .join(Website, Website.id == Post.website_id)
                .filter(
                    Post.platform_id == platform_id,
                    Website.domain_name == domain_name,
                    Organisation.name == organisation_name,
                )
                .one_or_none()
            )

            if not post:
                sentry_sdk.capture_message(
                    f"Post with platform_id {platform_id} not found in database for organisation {organisation_name} and domain {domain_name}",
                    level="warning",
                )
                return

            post.sent_to_counterfeit_platform = True
            post.scraping_status = ScrapingStatus.SENT
            session.commit()

    def update_post_filter_status(
        self, platform_id: str, organisation_id: int, website_id: int, status: ScrapingStatus
    ):
        with Session() as session:
            post = self._get(session, platform_id=platform_id, website_id=website_id, organisation_id=organisation_id)

            if not post:
                sentry_sdk.capture_message(
                    f"Post with platform_id {platform_id} not found in database for organisation {organisation_id} and domain {website_id}",
                    level="warning",
                )
                return

            if post.scraping_status == ScrapingStatus.SEARCHED:
                post.scraping_status = status

            session.commit()
