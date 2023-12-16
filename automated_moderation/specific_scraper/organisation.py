from .base_model import Base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)

    max_posts_to_counterfeit_platform_by_month = Column(Integer, nullable=True, unique=False)

    # { "en": [ "keyword1" , "keyword2", "keyword3"]}
    localized_keywords = Column(JSONB, default=lambda: {})
