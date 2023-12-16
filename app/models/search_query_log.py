from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship
from datetime import datetime

from .base_model import Base


class SearchQueryLog(Base):
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

    __tablename__ = "search_query_logs"

    id = Column(Integer, primary_key=True)

    search_query = Column(String, nullable=False, index=True)
    search_url = Column(String, nullable=False, index=True)

    task_log_id = Column(Integer, ForeignKey("tasks_logs.id"), nullable=True)
    task_log = relationship("TaskLog", backref=backref("search_query_logs"))

    start_date_time = Column(DateTime, nullable=False, default=datetime.now())
    end_date_time = Column(DateTime)

    # task limit for this search query
    max_posts_to_browse = Column(Integer)

    # task limit for max posts to discover per search query
    max_posts_to_discover = Column(Integer)

    # phase 1
    number_of_posts_discovered = Column(Integer)

    # phase 2
    number_of_posts_browse_attempts = Column(Integer)

    # phase 3
    number_of_posts_browsed = Column(Integer)

    # phase 4
    number_of_new_posts_found = Column(Integer)

    # phase 5
    number_of_posts_after_prefiltering = Column(Integer)

    # phase 6
    number_of_posts_scraped = Column(Integer)

    # phase 7
    number_of_posts_sent = Column(Integer)

    # to do delete **
    number_of_posts_with_search_info = Column(Integer)
