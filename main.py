import argparse
from app.dao import RedisDAO
from app.models.enums import ScrapingType
from app.service.task_runner.process_scrape_request import (
    scrape_by_task_id,
    scrape_posts_by_domain_keywords,
    scrape_posts_by_domain_name,
    scrape_posts_by_batch_key,
    scrape_accounts_by_batch_key,
    recrawl_instagram_profiles_batch,
    scrape_poster,
)


redis_DAO = RedisDAO()


if __name__ == "__main__":

    # Initiate arguments parser
    parser = argparse.ArgumentParser(
        description=(
            "This program executes a scraping tasks. You must specify the ID of the task to run "
            "or instead the organisation name, the website domain name and the search queries"
        )
    )

    parser.add_argument(
        "-st",
        "--scraping_type",
        type=str,
        help="Define Scrape Type",
        default=ScrapingType.POST_SEARCH_COMPLETE.name,
    )

    parser.add_argument("-t", "--task_id", type=int, help="specify the ID of the scraping task to run")

    parser.add_argument("-w", "--website_name", type=str, help="specify the domain name to scrape")

    parser.add_argument(
        "-r",
        "--from_rise",
        type=str,
        help="whether or not the posts are comming from RISE",
    )

    # If the flag --send_to_counterfeit_platform is provided, send_to_counterfeit_platform is set to True, else to False
    parser.add_argument(
        "-c",
        "--send_to_counterfeit_platform",
        dest="send_to_counterfeit_platform",
        action="store_true",
        help="specify whether to send the post to the Counterfeit Platform",
    )

    parser.set_defaults(send_to_counterfeit_platform=False)

    parser.add_argument(
        "-pu",
        "--posts_upload_batch_name",
        type=str,
        help="The Redis key where the URLs to scrape are stored along with their organisation, domain name, tags and label",
    )

    parser.add_argument(
        "-au",
        "--posters_upload_batch_name",
        type=str,
        help="The Redis key where the URLs to scrape are stored along with their organisation, domain name, tags and label",
    )

    parser.add_argument(
        "-iu",
        "--ig_users_batch_name",
        type=str,
        help="The Redis key where the details about the users to recrawl are stored",
    )

    parser.add_argument("-o", "--organisation_name", type=str, help="specify the organisation to use")

    parser.add_argument(
        "-s",
        "--search_queries",
        type=str,
        nargs="+",
        help="specify search queries to use",
    )

    # scrape poster info
    parser.add_argument(
        "-mpi",
        "--poster_info_scraping",
        type=str,
        help="The Redis key where the details about the marketplace posters to scrape are stored",
    )

    # scrape poster posts
    parser.add_argument(
        "-spp",
        "--scrape_poster_posts",
        dest="scrape_poster_posts",
        action="store_true",
        help="Specified if Poster Information Scraping should include poster posts Scrape",
    )
    parser.set_defaults(scrape_poster_posts=False)

    # scrape poster posts
    parser.add_argument(
        "-mpp",
        "--poster_posts_scraping",
        type=str,
        help="The Redis key where the details about the marketplace posters posts to scrape are stored",
    )

    parser.add_argument(
        "-purl",
        "--poster_url",
        type=str,
        help="The Poster Url to Scrape Posts For",
    )

    ## pass if you want logging or not
    parser.add_argument("-l", "--enable_logging", action="store_true", dest="enable_logging")
    parser.set_defaults(enable_logging=False)

    # Read command line arguments
    args = parser.parse_args()

    if args.task_id:
        scrape_by_task_id(args.task_id, args.enable_logging)

    elif args.from_rise:
        website_name = args.website_name
        scrape_posts_by_domain_name(website_name, args.enable_logging)

    elif args.posts_upload_batch_name:
        scrape_posts_by_batch_key(
            args.posts_upload_batch_name,
            send_to_counterfeit_platform=args.send_to_counterfeit_platform,
        )

    elif args.posters_upload_batch_name:
        scrape_accounts_by_batch_key(
            args.posters_upload_batch_name,
            send_to_counterfeit_platform=args.send_to_counterfeit_platform,
        )

    elif args.ig_users_batch_name:
        recrawl_instagram_profiles_batch(args.ig_users_batch_name)

    elif args.poster_info_scraping:
        # Task has been launched from RISE
        website_name = args.website_name

        posters = redis_DAO.get_posters_scraping_data(website_name, auto_delete=True)
        for poster in posters:
            scrape_poster(
                poster_url=poster,
                website_name=website_name,
                scrape_poster_posts=args.scrape_poster_posts,
                send_to_counterfeit_platform=True,
                enable_logging=args.enable_logging,
            )

    elif args.poster_posts_scraping:
        scrape_poster(
            poster_url=args.poster_url,
            website_name=args.website_name,
            scrape_poster_posts=True,
            send_to_counterfeit_platform=True,
            enable_logging=args.enable_logging,
        )

    else:
        scrape_posts_by_domain_keywords(
            organisation_name=args.organisation_name,
            domain_name=args.website_name,
            search_queries=args.search_queries,
            scraping_type=ScrapingType[args.scraping_type],
            enable_logging=args.enable_logging,
        )
