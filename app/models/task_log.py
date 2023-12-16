from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from .base_model import Base


class TaskLog(Base):
    """Possible numbers to track:

    0. [Theoretical] Number of posts found by the query. Requires infinite browsing to calculate in a general case. I add it here just for the context.
    1. Number of posts discovered. Depends on how far we've scrolled/paginated.
    2. Number of posts we _tried to browse_: essentially all from (1) except for ones that we skip for various reasons, e.g. seen in other queries in the same task.
    3. Number of posts browsed: can be different from (2) if extraction fails. The key counter that we typically limit and keep track of.
    4. Number of posts after removal of previously sent posts
    5. Number of posts after filtering
    6. Number of posts scraped
    7. Number of posts sent to the counterfeit platform
    """

    __tablename__ = "tasks_logs"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=True)

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    task = relationship("Task", backref=backref("task_logs", cascade="all, delete-orphan"))

    website_id = Column(Integer, ForeignKey("websites.id"), nullable=True)
    website = relationship("Website", backref=backref("tasks_logs", cascade="all, delete-orphan"))

    start_date_time = Column(DateTime, nullable=False, default=datetime.now())

    end_date_time = Column(DateTime)

    # counters for posts
    # phase 1
    number_of_posts_discovered = Column(Integer)

    # phase 2
    number_of_posts_browse_attempts = Column(Integer)

    # phase 3
    # This is equivalent to the number_of_posts_browsed in search_query_log. We will rename this later.
    number_of_results_founds = Column(Integer)

    # phase 4
    # This is equivalent to the number_of_new_posts_found in search_query_log. We will rename this later.
    number_of_new_results_found = Column(Integer)

    # phase 5
    # This is equivalent to the number_of_posts_after_prefiltering in search_query_log. We will rename this later.
    number_of_filtered_results_found = Column(Integer)

    # phase 6
    # This is equivalent to the number_of_posts_scraped in search_query_log. We will rename this later.
    number_of_complete_results_found = Column(Integer)  # number of posts that have all required information from domain

    # phase 7
    number_of_posts_sent = Column(Integer)

    # counters for posters
    number_of_posters_discovered = Column(Integer)
    number_of_posters_scraped = Column(Integer)

    post_extraction_info = Column(JSONB, default=lambda: {})

    light_posts_extraction_info = Column(JSONB, default=lambda: {})

    poster_extraction_info = Column(JSONB, default=lambda: {})

    payload = Column(JSONB, default=lambda: {})
