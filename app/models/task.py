from sqlalchemy import ARRAY, Boolean, Column, DateTime, ForeignKey, Integer, String, Enum

from sqlalchemy.orm import backref, relationship

from .base_model import Base
from app.models.enums import ScrapingType


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)

    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    organisation = relationship(
        "Organisation",
        backref=backref("tasks", cascade="all, delete-orphan"),
        lazy="joined",
    )

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    website = relationship("Website", backref=backref("tasks", cascade="all, delete-orphan"), lazy="joined")

    config_file = Column(String)  # If the config file name is not provided, the domain name is used to select it
    search_queries = Column(ARRAY(String))
    search_image_urls = Column(ARRAY(String))
    scraping_interval = Column(Integer)  # minimum time between two runs in seconds
    last_run_time = Column(DateTime)
    max_posts_to_browse = Column(Integer, nullable=True)
    max_posts_to_discover = Column(Integer, nullable=True)
    scraping_type = Column(Enum(ScrapingType), nullable=True, default=ScrapingType.POST_SEARCH_COMPLETE)

    send_posts_to_counterfeit_platform = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    task_revision = Column(Integer, nullable=True)
