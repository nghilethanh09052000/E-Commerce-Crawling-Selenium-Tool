# flake8: noqa
from sqlalchemy import create_engine
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.orm import Session as sa_session
from sqlalchemy_searchable import make_searchable

from .base_model import Base
from .settings import SS_DB_HOST, SS_DB_NAME, SS_DB_PASSWORD, SS_DB_PORT, SS_DB_USER
from .post import Post as SSPost
from .task import Task as SSTask
from .website import Website as SSWebsite
from .organisation import Organisation as SSOrganisation
from .light_post_log import LightPostLog as SSLightPostLog

engine = create_engine(
    "postgresql://{}:{}@{}:{}/{}".format(SS_DB_USER, SS_DB_PASSWORD, SS_DB_HOST, SS_DB_PORT, SS_DB_NAME),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=3600,
)


# It's important to make this call at this very moment in order to be able to make the database searchable
configure_mappers()

make_searchable(Base.metadata)

SessionMaker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Base.metadata.create_all(engine)


session_public_methods = [attr_name for attr_name in dir(sa_session) if not attr_name.startswith("__")]
