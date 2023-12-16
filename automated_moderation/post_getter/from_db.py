from typing import List, Optional, Tuple
from dataclasses import dataclass
from multiprocessing.pool import ThreadPool

from sqlalchemy.orm import joinedload, Session
from sqlalchemy import or_, func, and_
from rich.progress import Progress

from automated_moderation.utils.config import LABEL_TO_PREDICTION
from . import PostGetter
from automated_moderation.dataset import BasePost, BaseImage, BasePoster, BaseOrganisation, BaseCategory, BaseWebsite
from automated_moderation.utils.logger import log
from automated_moderation.utils.utils import query_by_batch, upload_image_from_url
from automated_moderation.specific_scraper import engine, SSPost, SSLightPostLog
from automated_moderation.specific_scraper.utils import get_post_platform_id
from eb_insertion_worker.post import translate_post_text
from app.models import Session as CounterfeitPlatformSession, Post, Website, TagMember, Tag, Label
from eb_insertion_worker import logger

logger.logger.disabled = True


@dataclass
class LightPostGetter(PostGetter):
    begin_date: Optional[str] = "2023-01-01"
    balance: bool = True

    def get(
        self, organisation_name: Optional[str] = None, domain_name: Optional[str] = None, tag: Optional[str] = None
    ) -> List[BasePost]:
        db_posts = self.get_moderation(organisation_name=organisation_name, domain_name=domain_name, tag=tag)
        log.info(f"Found {len(db_posts)} posts in database")

        db_post_by_platform_ids = {}
        with Progress() as progress:
            task_id = progress.add_task("Getting post platform id...", total=len(db_posts))
            with ThreadPool(5) as p:
                for light_post in p.imap(get_post_platform_id, db_posts):
                    if light_post:
                        db_post_by_platform_ids.update(light_post)
                    progress.advance(task_id)
        log.info(f"Found {len(db_post_by_platform_ids)} posts in database with platform ids")

        light_posts = self.get_light_posts(platform_ids=list(db_post_by_platform_ids.keys()))
        ligh_post_by_platform_ids = {post.platform_id: post for post in light_posts}
        log.info(f"Found {len(ligh_post_by_platform_ids)} posts in specific scraper")

        all_post_by_platform_id = {}
        for platform_id, db_post in db_post_by_platform_ids.items():
            if platform_id in ligh_post_by_platform_ids:
                all_post_by_platform_id[platform_id] = (db_post, ligh_post_by_platform_ids[platform_id])

        posts = []
        with Progress() as progress:
            task_id = progress.add_task("Converting to BasePost...", total=len(all_post_by_platform_id))
            with ThreadPool(50) as p:
                for post in p.imap(self.convert_to_base_post, all_post_by_platform_id.values()):
                    if post:
                        posts.append(post)
                    progress.advance(task_id)

        log.info(f"Found {len(posts)} base posts")

        self.detect_logos(posts=posts, organisation_name=organisation_name)

        return posts

    def convert_to_base_post(self, posts: Tuple[Post, SSPost]) -> Optional[BasePost]:
        db_post, light_post = posts

        # TODO: price conversion + price feature
        # TODO: location translation + location feature
        # TODO: source language feature

        if not light_post or not light_post.light_post_payload:
            return

        translated_title, translated_desc, source_language = translate_post_text(
            light_post.light_post_payload.get("title", ""),
            light_post.light_post_payload.get("description", ""),
            translation_activated=True,
        )

        return BasePost(
            id=db_post.id,
            url=light_post.light_post_payload["url"],
            label_name=db_post.label.name,
            organisation=BaseOrganisation(name=db_post.organisation.name),
            title=light_post.light_post_payload["title"],
            images=[
                BaseImage(
                    url=image_url if type(image_url) == str else image_url["picture_url"],
                    s3_url=image_url["s3_url"]
                    if (type(image_url) != str and image_url["s3_url"])
                    else upload_image_from_url(image_url if type(image_url) == str else image_url["picture_url"]),
                )
                for image_url in light_post.light_post_payload["pictures"]
            ],
            website=BaseWebsite(
                domain_name=db_post.website.domain_name,
                website_category=db_post.website.website_category.name if db_post.website.website_category else None,
            ),
            translated_title=translated_title,
            translated_description=translated_desc,
            source_language=source_language,
        )

    def get_light_posts(self, platform_ids: List[str]) -> List[SSPost]:
        with Session(engine) as session:
            subquery = (
                session.query(SSLightPostLog.platform_id, func.max(SSLightPostLog.id).label("max_id"))
                .filter(SSLightPostLog.platform_id.in_(platform_ids))
                .group_by(SSLightPostLog.platform_id)
                .subquery()
            )

            query = (
                session.query(SSLightPostLog)
                .join(
                    subquery,
                    and_(SSLightPostLog.platform_id == subquery.c.platform_id, SSLightPostLog.id == subquery.c.max_id),
                )
                .order_by(SSLightPostLog.id)
            )

            light_posts: List[SSLightPostLog] = query_by_batch(query=query)

            missing_light_posts = [
                platform_id
                for platform_id in platform_ids
                if platform_id not in [post.platform_id for post in light_posts]
            ]
            query = session.query(SSPost).filter(SSPost.platform_id.in_(missing_light_posts)).order_by(SSPost.id)

            light_posts += query_by_batch(query=query)

        return light_posts

    def get_moderation(
        self, organisation_name: Optional[str], domain_name: Optional[str], tag: Optional[str]
    ) -> List[Post]:
        log.info(f"Loading posts moderation from database for {organisation_name=}, {domain_name=} {tag=}...")

        relevant_labels = [label for label, prediction in LABEL_TO_PREDICTION.items() if prediction == 1]
        irrelevant_labels = [label for label, prediction in LABEL_TO_PREDICTION.items() if prediction == 0]

        with CounterfeitPlatformSession(organisation_name) as session:
            # Set seed for random
            session.execute("SELECT setseed(0.5)")

            query = (
                session.query(Post)
                .options(
                    joinedload(Post.label),
                    joinedload(Post.website),
                    joinedload(Post.website, Website.website_category),
                    joinedload(Post.organisation),
                )
                .filter(
                    Post.label_id != None, Post.moderation_date > self.begin_date, Post.source == "SPECIFIC_SCRAPER"
                )
                .order_by(func.random())
            )

            if domain_name:
                website_id: int = session.query(Website).filter(Website.domain_name == domain_name).one().id
                query = query.filter(Post.website_id == website_id)

            if tag:
                query = query.join(Post.tags).join(TagMember.tag).filter(Tag.name == tag)

            irrelevant_posts_query = query.join(Post.label).filter(Label.name.in_(irrelevant_labels))
            relevant_posts_query = query.join(Post.label).filter(Label.name.in_(relevant_labels))
            limit = min(irrelevant_posts_query.count(), relevant_posts_query.count()) if self.balance else None

            irrelevant_posts = query_by_batch(query=irrelevant_posts_query, limit=limit)
            relevant_posts = query_by_batch(query=relevant_posts_query, limit=limit)

        return irrelevant_posts + relevant_posts


@dataclass
class DBPostGetter(PostGetter):
    one_image: bool = False

    def get(
        self, organisation_name: Optional[str] = None, domain_name: Optional[str] = None, tag: Optional[str] = None
    ) -> List[BasePost]:
        db_posts = self.get_posts_from_db(organisation_name=organisation_name, domain_name=domain_name, tag=tag)
        print(f"Found {len(db_posts)} posts in database")

        posts = [
            BasePost(
                id=post.id,
                images=[
                    BaseImage(
                        logo_detected=image.logo_detected,
                        s3_url=image.s3_url,
                        url=image.url,
                    )
                    for image in post.images
                ],
                title=post.title,
                description=post.description,
                organisation=BaseOrganisation(name=post.organisation.name),
                url=post.link,
                translated_title=post.translated_title,
                translated_description=post.translated_description,
                category=BaseCategory(name=post.category.name) if post.category else None,
                website=BaseWebsite(
                    domain_name=post.website.domain_name,
                    website_category=post.website.website_category.name,
                ),
                poster=BasePoster(
                    id=post.poster.id,
                    name=post.poster.name,
                )
                if post.poster
                else None,
                label_name=post.label.name,
            )
            for post in db_posts
        ]

        if self.one_image:
            for post in posts:
                post.images = post.images[:1]

        self.detect_logos(posts=posts)
        return posts

    def get_posts_from_db(
        self, organisation_name: Optional[str], domain_name: Optional[str], tag: Optional[str]
    ) -> List[Post]:
        log.info(f"Loading posts moderation from database for {organisation_name=}, {domain_name=} {tag=}...")

        with CounterfeitPlatformSession(organisation_name) as session:

            query = (
                session.query(Post)
                .options(
                    joinedload(Post.label),
                    joinedload(Post.website),
                    joinedload(Post.website, Website.website_category),
                    joinedload(Post.organisation),
                    joinedload(Post.images),
                    joinedload(Post.poster),
                    joinedload(Post.category),
                )
                .filter(
                    Post.label_id != None,
                )
                .order_by(Post.id)
            )

            if domain_name:
                website_id: int = session.query(Website).filter(Website.domain_name == domain_name).one().id
                query = query.filter(Post.website_id == website_id)

            if tag:
                query = query.join(Post.tags).join(TagMember.tag).filter(Tag.name == tag)

            return query_by_batch(query=query)


@dataclass
class ISDescCounterfeitPostGetter(PostGetter):
    def get(
        self, organisation_name: Optional[str] = None, domain_name: Optional[str] = None, tag: Optional[str] = None
    ) -> List[BasePost]:
        return [
            BasePost(
                id=post.id,
                images=[],
                title=post.title,
                description=post.description,
                organisation=post.organisation,
                translated_title=post.translated_title,
                translated_description=post.translated_description,
                label_name=post.label.name if post.label else None,
                is_desc_counterfeit=post.is_desc_counterfeit,
                weight=self.weight,
            )
            for post in self.get_posts_from_db()
        ]

    def get_posts_from_db(self) -> List[Post]:
        with Session() as session:
            true_label_count = session.query(Post).filter(Post.is_desc_counterfeit == True).count()
            false_label_count = session.query(Post).filter(Post.is_desc_counterfeit == False).count()
            limit = min(true_label_count, false_label_count)

            q = (
                session.query(Post)
                .options(
                    joinedload(Post.organisation),
                    joinedload(Post.label),
                )
                .filter(or_(Post.translated_title.isnot(None), Post.translated_description.isnot(None)))
            )

            posts = q.filter(Post.is_desc_counterfeit == True).limit(limit).all()
            posts += q.filter(Post.is_desc_counterfeit == False).limit(limit).all()

        return posts
