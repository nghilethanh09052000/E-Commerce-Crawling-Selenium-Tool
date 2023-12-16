from datetime import datetime, timezone

from app.models import Session, SearchQueryLog


class SearchQueryLogDAO:
    def create(self, search_query: str, search_url: str, task_log_id: int) -> SearchQueryLog:
        with Session() as session:
            search_query_log = SearchQueryLog(
                search_query=search_query,
                search_url=search_url,
                task_log_id=task_log_id,
                start_date_time=datetime.now(timezone.utc),
            )
            session.add(search_query_log)
            session.commit()

        return search_query_log

    def end(
        self,
        search_query_log_id: int,
        number_of_posts_browsed: int,
        number_of_posts_discovered: int,
        max_posts_to_browse: int,
        max_posts_to_discover: int,
    ):
        with Session() as session:
            search_query_log: SearchQueryLog = session.query(SearchQueryLog).get(search_query_log_id)
            search_query_log.number_of_posts_browsed = number_of_posts_browsed
            search_query_log.number_of_posts_discovered = number_of_posts_discovered
            search_query_log.max_posts_to_browse = max_posts_to_browse
            search_query_log.max_posts_to_discover = max_posts_to_discover
            search_query_log.end_date_time = datetime.now(timezone.utc)
            session.commit()
