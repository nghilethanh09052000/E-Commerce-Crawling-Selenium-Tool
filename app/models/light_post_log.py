from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Float, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import backref, relationship

from .base_model import Base


class LightPostLog(Base):
    __tablename__ = "light_post_logs"

    __table_args__ = (
        Index("ix_light_post_logs_website_id_organisation_id_time", "website_id", "time", "organisation_id"),
        Index("ix_light_post_logs_website_id_time", "website_id", "time"),
    )

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, server_default=func.now(), nullable=False)
    platform_id = Column(String, nullable=False, index=True)

    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=True,
        index=True,
    )
    organisation = relationship(
        "Organisation",
        backref=backref("light_post_logs", cascade="all, delete-orphan"),
    )

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    website = relationship("Website", backref=backref("light_post_logs", cascade="all, delete-orphan"))

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    task = relationship("Task", backref=backref("light_post_logs"))

    light_post_payload = Column(JSONB)
    filter_post_payload = Column(JSONB)

    risk_score = Column(Float, nullable=True)
