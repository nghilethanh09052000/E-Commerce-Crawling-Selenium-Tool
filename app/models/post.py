from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
    Enum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref, relationship
from sqlalchemy_utils.types import TSVectorType
from app.models.enums import ScrapingStatus

from .base_model import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)

    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
    )
    organisation = relationship(
        "Organisation",
        backref=backref("posts", cascade="all, delete-orphan"),
    )

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    website = relationship("Website", backref=backref("posts", cascade="all, delete-orphan"))

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    task = relationship("Task", backref=backref("posts"))

    platform_id = Column(String, index=True)
    scraping_time = Column(DateTime, index=True)
    url = Column(String)

    scraping_status = Column(Enum(ScrapingStatus), nullable=True, default=ScrapingStatus.SEARCHED, index=True)

    # TODO: delete this column after scraping status has been updated
    sent_to_counterfeit_platform = Column(Boolean, default=False)

    # TODO: delete this column when everything use the new save logic
    light_post_payload = Column(JSONB, default=lambda: {})

    url = Column(String)
    title = Column(String)
    description = Column(String)
    price = Column(String)
    stock_count = Column(String)
    pictures = Column(ARRAY(String))
    videos = Column(ARRAY(String))
    risk_score = Column(Float)
    archive_link = Column(String)
    posting_time = Column(DateTime)

    vendor = Column(String)
    poster_link = Column(String)
    poster_website_identifier = Column(String)

    location = Column(String)
    ships_from = Column(JSONB, default=lambda: {})
    ships_to = Column(JSONB, default=lambda: {})

    alternate_links = Column(ARRAY(String))

    # Add possibility to search in columns title and description
    search_vector = Column(TSVectorType("title", "description"))

    # Set a unicity contraint over organisation_id + website_id + platform_id
    __table_args__ = (
        UniqueConstraint("organisation_id", "website_id", "platform_id"),
        Index(
            "ix_posts_website_id_patform_id_sent_to_counterfeit_platform_org",
            "website_id",
            "platform_id",
            "sent_to_counterfeit_platform",
            "organisation_id",
        ),
        Index(
            "ix_posts_website_id_scraping_status_scraping_time_platform_id",
            "website_id",
            "scraping_status",
            "scraping_time",
            "platform_id",
        ),
        Index("ix_posts_website_id", "website_id"),
        Index(
            "ix_posts_web_id_scraping_stats_scraping_time_platform_id_org_id",
            "website_id",
            "scraping_status",
            "scraping_time",
            "platform_id",
            "organisation_id",
        ),
        Index(
            "ix_posts_org_id_id_website_id_scraping_status_risk_score",
            "organisation_id",
            "id",
            "website_id",
            "scraping_status",
            "risk_score",
        ),
    )

    @property
    def serialize(self):
        return {
            "id": self.id,
            "platform_id": self.platform_id,
            "scraping_time": self.scraping_time,
            "url": self.url,
        }

    @property
    def serialize_full(self):
        return {
            "id": self.id,
            "platform_id": self.platform_id,
            "scraping_time": self.scraping_time,
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "pictures": self.pictures,
            "videos": self.videos,
            "risk_score": self.risk_score,
            "archive_link": self.archive_link,
            "posting_time": self.posting_time,
            "vendor": self.vendor,
            "poster_link": self.poster_link,
            "poster_website_identifier": self.poster_website_identifier,
            "location": self.location,
            "ships_from": self.ships_from,
            "ships_to": self.ships_to,
            "search_vector": self.search_vector,
            "light_post_payload": self.light_post_payload,
        }
