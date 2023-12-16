from datetime import datetime, timezone

from sqlalchemy import distinct
from sqlalchemy.exc import IntegrityError

from app.models import Poster, Session

from .utils import safe_bulk_update_mappings
from .website import WebsiteDAO

website_dao = WebsiteDAO()


class PosterDAO:
    def create(self, website_id, poster_url, name):
        with Session() as session:
            poster = Poster(
                website_id=website_id,
                url=poster_url,
                name=name,
                scraping_time=datetime.now(timezone.utc),
            )
            session.add(poster)
            session.commit()

            return poster

    def get_poster(self, website_id, poster_url, name, auto_create=False):
        with Session() as session:
            poster = (
                session.query(Poster).filter(Poster.website_id == website_id).filter(Poster.url == poster_url).first()
            )
        if not poster and auto_create is True:
            poster = self.create(website_id, poster_url, name)
        return poster

    def bulk_update_posters_in_db(self, posters):
        return safe_bulk_update_mappings(mapper=Poster, mappings=posters)

    def get_unscraped_instagram_usernames(self, usernames):
        instagram = website_dao.get("instagram.com")

        with Session() as session:
            # Select all the Instagram usernames which have previously been scraped and saved to the database
            scraped_usernames_query = (
                session.query(distinct(Poster.name))
                .filter(Poster.website_id == instagram.id)
                .filter(Poster.name.in_(usernames))
            )

            scraped_usernames = [row[0] for row in scraped_usernames_query.all()]

        unscraped_usernames = list(set(usernames) - set(scraped_usernames))

        return unscraped_usernames

    def upsert_profile(
        self,
        username,
        website,
        description,
        url,
        profile_pic_url,
        posts_count,
        followers_count,
        poster_website_identifier,
    ):
        NOW = datetime.now(timezone.utc)

        with Session() as session:
            try:
                profile_object = Poster(
                    name=username,
                    website=website,
                    description=description,
                    url=url,
                    profile_pic_url=profile_pic_url,
                    posts_count=posts_count,
                    followers_count=followers_count,
                    scraping_time=NOW,
                    poster_website_identifier=poster_website_identifier,
                )
                session.add(profile_object)
                session.commit()

            except IntegrityError:
                session.rollback()

                profile_object = (
                    session.query(Poster)
                    .filter_by(
                        website=website,
                        name=username,
                    )
                    .one()
                )

                if (
                    profile_object.description != description
                    or profile_object.url != url  # noqa:W503
                    or profile_object.profile_pic_url != profile_pic_url  # noqa:W503
                    or profile_object.posts_count != posts_count  # noqa:W503
                    or profile_object.followers_count != followers_count  # noqa:W503
                    or profile_object.poster_website_identifier != poster_website_identifier
                ):
                    profile_object.description = description
                    profile_object.url = url
                    profile_object.profile_pic_url = profile_pic_url
                    profile_object.posts_count = posts_count
                    profile_object.followers_count = followers_count
                    profile_object.poster_website_identifier = poster_website_identifier

                    session.commit()

            return profile_object

    def set_profile_archive_link(self, profile_object: Poster, archive_link: str):
        with Session() as session:
            profile = session.query(Poster).get(profile_object.id)

            profile.archive_link = archive_link

            session.commit()

        return profile

    def set_profile_sent_status(self, profile_object: Poster, sent_status: bool):
        with Session() as session:
            profile = session.query(Poster).get(profile_object.id)

            profile.sent_to_counterfeit_platform = sent_status

            session.commit()
