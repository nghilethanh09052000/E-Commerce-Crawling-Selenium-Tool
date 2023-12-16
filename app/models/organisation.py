from .base_model import Base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)

    max_posts_to_counterfeit_platform_by_month = Column(Integer, nullable=True, unique=False)

    activate_filtering = Column(Boolean, nullable=False, default=False, server_default="false")

    # list of keywords separated by comma
    exclude_keywords = Column(
        String, nullable=True
    )  # If a post has at least one of the listed keywords, then filter it out
    must_have_keywords = Column(
        String, nullable=True
    )  # Post should have at least one of the keywords, or else filter it out

    # { "en": [ "keyword1" , "keyword2", "keyword3"]}
    localized_keywords = Column(JSONB, default=lambda: {})
