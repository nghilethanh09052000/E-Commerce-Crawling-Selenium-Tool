# flake8: noqa
from app.settings import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, scoped_session, sessionmaker
from sqlalchemy.orm import Session as sa_session
from sqlalchemy_searchable import make_searchable

from .base_model import Base
from .website import Website
from .post import Post
from .organisation import Organisation
from .task import Task
from .task_log import TaskLog
from .profile import Poster
from .country_locale import country_code_locale
from .chromeprofile import Chromeprofile
from .scraping_attempt import ScrapingAttempt
from .scraped_post_log import ScrapedPostLog
from .light_post_log import LightPostLog
from .search_query_log import SearchQueryLog

engine = create_engine(
    "postgresql://{}:{}@{}:{}/{}".format(DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=3600,
)


# It's important to make this call at this very moment in order to be able to make the database searchable
configure_mappers()

make_searchable(Base.metadata)

Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
