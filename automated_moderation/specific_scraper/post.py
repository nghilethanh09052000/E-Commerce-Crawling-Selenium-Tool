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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref, relationship
from sqlalchemy_utils.types import TSVectorType

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
    posting_time = Column(DateTime)

    url = Column(String)

    # Define a property to state whether the post has already been sent to the Counterfeit Platform
    sent_to_counterfeit_platform = Column(Boolean, default=False)

    url = Column(String)
    title = Column(String)
    description = Column(String)
    price = Column(String)
    pictures = Column(ARRAY(String))
    risk_score = Column(Float)
    archive_link = Column(String)
    posting_time = Column(DateTime)
    location = Column(String)
    ships_from = Column(JSONB, default=lambda: {})
    ships_to = Column(JSONB, default=lambda: {})
    poster_link = Column(String)
    poster_website_identifier = Column(String)

    vendor = Column(String)
    poster_link = Column(String)
    poster_website_identifier = Column(String)

    location = Column(String)
    ships_from = Column(JSONB, default=lambda: {})
    ships_to = Column(JSONB, default=lambda: {})

    # Add possibility to search in columns title and description
    search_vector = Column(TSVectorType("title", "description"))

    # Dump of what the post looks like at search time
    light_post_payload = Column(JSONB, default=lambda: {})

    # Set a unicity contraint over organisation_id + website_id + platform_id
    __table_args__ = (
        UniqueConstraint("organisation_id", "website_id", "platform_id"),
        Index(
            "ix_posts_website_id_patform_id_sent_to_counterfeit_platform_organisation_id",
            "website_id",
            "platform_id",
            "sent_to_counterfeit_platform",
            "organisation_id",
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
