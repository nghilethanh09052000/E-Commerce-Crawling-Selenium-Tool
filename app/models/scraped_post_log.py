from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref, relationship

from .base_model import Base


class ScrapedPostLog(Base):
    __tablename__ = "scraped_post_logs"

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, server_default=func.now(), nullable=False)
    platform_id = Column(String, nullable=False, index=True)

    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
    )
    organisation = relationship(
        "Organisation",
        backref=backref("scraped_post_logs", cascade="all, delete-orphan"),
    )

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    website = relationship("Website", backref=backref("scraped_post_logs", cascade="all, delete-orphan"))

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    task = relationship("Task", backref=backref("scraped_post_logs"))

    post_payload = Column(JSONB)
