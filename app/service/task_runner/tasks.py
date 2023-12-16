from typing import Dict

from app.models.enums import ScrapingType

from .ecs import create_ecs_container


def launch_scraping_task(
    scraping_type: ScrapingType = None,
    task_id=None,
    organisation_name=None,
    website_name=None,
    search_queries=None,
    send_to_counterfeit_platform=False,
    from_rise=False,
    posts_upload_batch_name=None,
    posters_upload_batch_name=None,
    ig_users_batch_name=None,
    poster_info_scraping=None,
    poster_posts_scraping=None,
    send_to_s3=False,
    scrape_poster_posts=False,
    config_file=None,
    tags: Dict[str, str] = {},
    poster_url: str = None,
    task_revision: int = None,
):
    command = ["python3"]
    command += ["main.py", "--enable_logging"]

    started_by_sentence = None

    if not task_revision:
        task_revision = 12

    if scraping_type:
        command += ["--scraping_type", str(scraping_type.name)]

    if task_id:
        command += ["--task_id", str(task_id)]
        tags.update({"SSTaskId": task_id})
        tags.update({"Website": website_name})
        tags.update({"Organisation": organisation_name})

    elif from_rise:
        command += ["--from_rise", str(1)]
        command += ["--website_name", website_name]
        started_by_sentence = f"RISE recrawling on {website_name}"

    elif posts_upload_batch_name:
        command += ["--posts_upload_batch_name", posts_upload_batch_name]
        started_by_sentence = f"Scraping posts upload batch {posts_upload_batch_name}"

    elif posters_upload_batch_name:
        command += ["--posters_upload_batch_name", posters_upload_batch_name]
        started_by_sentence = f"Scraping posters upload batch {posters_upload_batch_name}"

    elif ig_users_batch_name:
        command += ["--ig_users_batch_name", ig_users_batch_name]
        started_by_sentence = f"Scraping Instagram profiles batch {ig_users_batch_name}"

    elif poster_info_scraping:
        command += ["--poster_info_scraping", str(1)]
        command += ["--website_name", website_name]
        if scrape_poster_posts:
            command += ["--scrape_poster_posts"]
        started_by_sentence = f"Scraping Posters Info for {website_name}"

    elif poster_posts_scraping:
        command += ["--poster_posts_scraping", str(1)]
        command += ["--website_name", website_name]
        command += ["--scrape_poster_posts"]
        command += ["--poster_url", poster_url]

        started_by_sentence = f"Scraping Poster Posts for {website_name}"

    else:
        command += [
            "--organisation_name",
            organisation_name,
            "--website_name",
            website_name,
        ]
        command += ["--search_queries"] + [q for q in search_queries]

    if send_to_counterfeit_platform:
        # send_to_counterfeit_platform is set to True i.i.f the flag --send_to_counterfeit_platform is provided
        command += ["--send_to_counterfeit_platform"]

    if send_to_s3:
        command += ["--send_to_s3"]

    if not started_by_sentence:
        started_by_sentence = f"task {task_id}" if task_id else f"{website_name} for {organisation_name}"

    response = create_ecs_container(command, started_by_sentence, task_revision, tags=tags)

    return response


def run_script_in_ecs(command, name):
    """This function is useful to run a command different from scraper/main.py --task_id"""

    if type(command) is str:
        command = command.split(" ")
    started_by_sentence = name

    response = create_ecs_container(command, started_by_sentence)

    return response
