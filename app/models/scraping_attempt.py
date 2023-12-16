from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Enum, Index
from sqlalchemy.orm import backref, relationship

from .base_model import Base
from app.models.enums import RequestResult


class ScrapingAttempt(Base):
    __tablename__ = "scraping_attempts"

    __table_args__ = (
        Index("ix_proxy", "proxy_provider", "proxy_country"),
        Index("ix_scraping_attempts_proxy_provider_request_result_time", "proxy_provider", "request_result", "time"),
        Index("ix_scraping_attempts_dashboard3", "proxy_provider", "time", "website_id", "request_result"),
        Index("ix_scraping_attempts_dashboard2", "proxy_provider", "website_id", "request_result", "time"),
        Index("ix_scraping_attempts_dashboard1", "proxy_provider", "request_result", "website_id", "time"),
        Index("ix_scraping_attempts_website_id_time", "website_id", "time"),
        Index(
            "ix_scraping_attempts_time_proxy_provider_request_result_website",
            "time",
            "proxy_provider",
            "request_result",
            "website_id",
        ),
    )

    id = Column(Integer, primary_key=True)

    time = Column(DateTime, nullable=False)

    url = Column(String, nullable=False)
    page_title = Column(String)
    screenshot = Column(String)

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False, index=True)
    website = relationship("Website", backref=backref("scraping_attempts"))

    proxy_provider = Column(String, index=True)
    proxy_country = Column(String)
    proxy_ip = Column(String)

    request_result = Column(Enum(RequestResult), nullable=False)
    error_message = Column(String)
