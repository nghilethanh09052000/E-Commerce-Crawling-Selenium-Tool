from .base_model import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import backref, relationship


class Chromeprofile(Base):
    __tablename__ = "chromeprofiles"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False, unique=True)

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    website = relationship("Website", backref=backref("chromeprofiles", cascade="all, delete-orphan"))

    credentials = Column(String)
