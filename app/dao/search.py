from app.models import Post, Session
from sqlalchemy_searchable import search as sqlalchemy_search


class SearchDAO:
    def db_search(self, saved_posts, full_text_query, organisation_name=None):
        """Make a full text search over the table Post among saved_posts

        Available operators: AND, OR, NOT, parentheses

        Args:
            saved_posts (dict)
            full_text_query (str): see https://sqlalchemy-searchable.readthedocs.io/en/latest/search_query_parser.html#search-query-parser
            organisation_name (str or None)

        Returns:
            selected_post_ids (int[]): IDs of Post objects matching the query
        """

        # Only the lowercase OR operator is parsed by the search() function
        full_text_query = full_text_query.replace(" OR ", " or ")

        # The AND operator is not recognized but it is the default operator
        full_text_query = full_text_query.replace(" AND ", " ")

        # The NOT operator is a dash (-)
        full_text_query = full_text_query.replace(" NOT ", " - ")

        saved_post_ids = [post_object.id for post_object in saved_posts.values()]

        with Session() as session:
            sql_query = (
                session.query(Post).filter(Post.id.in_(saved_post_ids)).filter(Post.pictures.isnot(None)).distinct()
            )

            search_query = sqlalchemy_search(sql_query, full_text_query, regconfig="pg_catalog.simple")

            selected_post_ids = [row[0] for row in search_query.with_entities(Post.id).all()]

        return selected_post_ids
