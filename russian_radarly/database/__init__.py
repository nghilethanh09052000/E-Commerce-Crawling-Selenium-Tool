from enumerator import QueryType
from rr_settings import (API_TOKEN, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT,
                         DB_USER)
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as ALchemyEnum
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Index

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}", pool_pre_ping=True, pool_size=1
)

Session = sessionmaker(engine)

Base = declarative_base()


class QueryLog(Base):
    __tablename__ = "query_log"
    __table_args__ = (
        Index("query_type_idx", "query_type"),
        Index("time_of_call_response_time_idx", "time_of_call", "response_time"),
        Index("status_description_code_idx", "status", "description", "code"),
    )

    id = Column(Integer, primary_key=True)
    query = Column(String, nullable=False)
    query_type = Column(ALchemyEnum(QueryType), nullable=False)
    time_of_call = Column(DateTime, nullable=False)
    response_time = Column(Integer, nullable=False)  # in milliseconds
    status = Column(String)
    description = Column(String)
    code = Column(String)


# Base.metadata.create_all(engine)
