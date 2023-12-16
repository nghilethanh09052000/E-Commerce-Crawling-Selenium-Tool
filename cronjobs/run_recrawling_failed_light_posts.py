"""This script runs recrawling for failed light"""

from app import logger
from app.models import Session
from app.service.send import send_scraping_task


def get_posts_to_recrawl():
    query = """
        WITH rp AS (
            SELECT
                row_number() OVER (ORDER BY p.id) rn,
                o."name" organisation_name, w.domain_name, platform_id post_identifier
            FROM posts p
            JOIN websites w ON p.website_id = w.id
            JOIN organisations o ON p.organisation_id = o.id
            WHERE p.id > (
                SELECT LAST_VALUE - 1000000 FROM posts_id_seq
            )
            AND scraping_status = 'FILTERED_IN'
        )
        SELECT organisation_name, domain_name, post_identifier
        FROM (
            SELECT DISTINCT 1 + trunc(random() * (SELECT count(*) FROM rp))::integer AS rn
            FROM generate_series(1, 1100) g
            LIMIT 1000
        ) r
        JOIN rp USING (rn)
        ;
    """
    tasks = list()
    with Session() as session:
        posts = session.execute(query)
        for post in posts:
            task = dict(post)
            task["page_type"] = "POST"
            tasks.append(task)
    assert tasks, "No posts to recrawl"
    return tasks


if __name__ == "__main__":
    logger.input("Getting posts to recrawl", call_name="run_recrawling_failed_light_posts")
    tasks = get_posts_to_recrawl()
    logger.info("Sending posts to recrawl")
    for task in tasks:
        send_scraping_task(task)
    logger.output("Posts are sent")
