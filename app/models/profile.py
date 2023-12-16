from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql.schema import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .base_model import Base


class Poster(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    poster_website_identifier = Column(String)

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    website = relationship("Website", backref=backref("profiles", cascade="all, delete-orphan"))

    description = Column(Text)  # User description/biography
    url = Column(String)
    profile_pic_url = Column(String)
    archive_link = Column(String)
    posts_count = Column(Integer)
    followers_count = Column(Integer)
    scraping_time = Column(DateTime, nullable=False)
    payload = Column(JSONB, default=lambda: {})

    sent_to_counterfeit_platform = Column(Boolean)

    __table_args__ = (UniqueConstraint("name", "website_id", name="profiles_name_website_uc"),)
