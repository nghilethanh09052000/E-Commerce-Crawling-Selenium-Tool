import copy
import json
import traceback
from copy import deepcopy
from datetime import datetime, timezone

from navee_utils.domain_helper import get_domain_name_from_url
import timeout_decorator
from app import app
from app.dao import PosterDAO
from app.models import (
    Image,
    InfexLog,
    InformationExtractionResult,
    Post,
    Session,
    SpecificScraperWebsite,
    Website,
    engine,
)
from app.settings import ENVIRONMENT_NAME, sentry_sdk
from app.utils.analyze_infex_results import update_takedown_status_from_infex_results
from app.utils.miscellaneous import requires_scroll_smoothly
from app.utils.price import get_price_data
from app.utils.robustness import log_args
from app.utils.tasks_sender import send_insertion_task, send_scraping_task
from app.utils.text_translation import get_text_language, translate_text_into_english
from app.utils.url import is_not_a_post_url
from eb_infex_worker import logger
from flask import Response, request
from sqlalchemy.orm import joinedload
from timeout_decorator.timeout_decorator import TimeoutError

from eb_infex_worker.information_extraction.main import infex_single_website

engine.dispose()

WORKER_TIMEOUT = 200

poster_dao = PosterDAO()


@app.route("/", methods=["POST"])
@timeout_decorator.timeout(WORKER_TIMEOUT)
def extract_information_from_post():

    logger.input(call_name="extract_information_from_post", message="Running infex worker for post")

    body = request.get_json()

    post_id = body.get("post_id")
    organisation_id = body.get("organisation_id")
    is_web_monitor = body.get("is_web_monitor", False)

    try:
        if is_web_monitor:
            check_pattern_for_webmonitor(post_id, organisation_id)
        else:
            worker_information_extraction(body, post_id, organisation_id)
    except TimeoutError:

        # Log the timeout
        post_identifier = post_id if post_id else None
        post_url = body["post"]["url"]
        logger.warn(message="Worker timeout for post", post_link=post_url, post_id=post_identifier)

        # Report to Sentry
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("error-type", "infex-worker-timeout")
            scope.set_extra("post_id", post_id)
            scope.set_extra("body", body)
            scope.set_extra("is_web_monitor", is_web_monitor)
            sentry_sdk.capture_message("Worker timeout")

        # Note: https://www.notion.so/3-Infex-issues-e678194d2ad0469cb33d0b6e95e55cd2
        # Previously there was no "raise", so timeouts were never retried. Now with "raise" sentry errors are
        # duplicated, with both capture_message and general-case handling of gunicorn http errors. We can
        # remove capture_message in the future, but I've kept it for now to see the effect on the same graph
        # in sentry (and also structured logs are nice).
        raise

    logger.output(message="Finished Extracting information")

    return Response(status="200")


@log_args
def worker_information_extraction(
    post_body=None,
    post_id=None,
    organisation_id=None,
    send_insertion_tasks=True,
    page_timeout_override=None,
    element_timeout_override=None,
    use_navee_driver=False,
):
    """Add a post to Counterfeit Platform and RISE databases

    We add a timeout decorator to be able to catch the timeout cases (which can be legit e.g. when a website is very slow)
    instead of raising WORKER_TIMEOUT errors with no context in Sentry

    Parameters
    ----------
    post_id: int, optional
        if post_id is provided, it is handled instead of post_body
    organisation_id: int, optional
        if post_id is provided, organisation_id must be provided too
    post_body: dictionary with the following keys
        environment_name: str, required
        organisation_name: str, required
        item: dict, required
            dictionary containing post information
        search_in_rise: bool, optional, default True
            if defined and set to False, do not make any call to RISE
        launch_archiving: bool, optional, default True
            if defined and set to False, do not send the archiving task
        launch_classifying: bool, optional default True
            if defined and set to False, do not send the classifying task
        launch_logo_detection: bool, optional default True
            if defined and set to False, do not send the classifying task

    post: dictionary which may contain the following keys
        price: str
        scraping_time: str
        category: str
        poster: str
        url: str
        title: str
        description: str
        source: str
        payload: str
        post_label: str
            label name
        post_tags: str[]
            tags under which the post should be recorded
        post_tag: str
            tag under which the post should be recorded - post_tags takes precedence over post_tag
        image_label: str
        archive_link: str
        pictures: []
            The list pictures can contain both strings and dictionaries.
            If an item in pictures is a string, it is an image URL;
            if an item in pictures is a dictionary, it has keys the "picture_url", "s3_url" and "duplicated_group_id",
            and the image S3 URL and duplicated group ID may have been previously determined
    """

    posts_to_insert = []

    if post_id:

        # Enrich the information of an existing post
        assert organisation_id

        with Session(organisation_id) as session:

            # If the key post_id is provided but the post is not found, a NoResultsFound error is raised by sqlalchemy
            post = (
                session.query(Post)
                .filter_by(id=post_id)
                .options(
                    joinedload(Post.website),
                    joinedload(Post.images),
                    joinedload(Post.organisation),
                    joinedload(Post.poster),
                )
                .one()
            )

            # The post is already stored in db: we set the price and title if we find some and create new posts if needed
            logger.info(
                message=f"Enrich information for post: {post_id}",
                post_link=post.link,
                post_id=post_id,
            )

            # We can't properly process the posts from websites which we can't monitor
            website = post.website
            if not website.can_monitor:
                return

            scroll_smoothly = False

            if requires_scroll_smoothly(post.link):
                logger.info(message="domain requires scrolling", post_link=post.link, post_id=post_id)
                scroll_smoothly = True

            for image in post.images:
                (
                    extracted_page_url,
                    title,
                    price,
                    description,
                    poster,
                    pattern_detected,
                    infex_error,
                ) = infex_single_website(
                    post.link,
                    image.url,
                    image.s3_url,
                    scroll_smoothly=scroll_smoothly,
                    page_timeout_override=page_timeout_override,
                    element_timeout_override=element_timeout_override,
                    use_navee_driver=use_navee_driver,
                )

                logger.info(
                    message="Output of extract_meta_information: "
                    f"{(extracted_page_url, title, price, description, poster, pattern_detected, infex_error)}",
                    post_link=post.link,
                    post_id=post_id,
                    image_id=image.id,
                    image_link=image.s3_url,
                )

                # Record the output of the information extraction in database (replace if already exists)
                session.query(InformationExtractionResult).filter_by(id=image.id).delete()

                infex_result = InformationExtractionResult(
                    id=image.id,
                    image_found=True if extracted_page_url else False,
                    pattern_detected=True if pattern_detected else False,
                    price_detected=True if price else False,
                    title_detected=True if title else False,
                    description_detected=True if description else False,
                    poster_detected=True if poster else False,
                    execution_date=datetime.now(timezone.utc),
                    error=infex_error,
                )
                session.add(infex_result)
                session.commit()

                if extracted_page_url is not None:

                    if extracted_page_url != post.link:
                        # Most likely, the image contains a href linking to a product page

                        logger.info(
                            f"A page URL different from the post URL has been extracted: {extracted_page_url}",
                            post_link=post.link,
                            post_id=post_id,
                            image_id=image.id,
                            image_link=image.s3_url,
                        )

                        # Build a post body with the appropriate image data and send it to the insertion worker
                        new_post_body = build_new_post_body_from_image_object(
                            image, extracted_page_url, title, price, description, poster, pattern_detected
                        )

                        # delete the image, without cascade deletions (we don't want to delete the duplicated group)
                        # Since cascade deletion is disabled, we delete the information extraction result if it exists
                        session.query(InformationExtractionResult).filter_by(id=image.id).delete()
                        session.query(Image).filter_by(id=image.id).delete()
                        session.commit()

                        logger.debug("The image is a relevant reference")

                        if send_insertion_tasks:
                            send_task(new_post_body)
                        else:
                            posts_to_insert.append(new_post_body)

                    else:

                        # TODO: in the worker refacto, there is some code factorization to do with the Insertion Worker

                        logger.info("Extracting information")

                        (original_price, original_currency, organisation_currency_price,) = get_price_data(
                            price,
                            post.organisation.currency,
                            post.website.domain_name,
                            post.website.country_code,
                        )

                        # Update the title and price of the current post if necessary
                        if title and (not post.title or post.source.value == "not_reliable"):
                            # Override the title only if no title is yet defined or the source isn't navee_scraper
                            logger.info(
                                f"Update title: {post.title} -> {title}",
                                post_link=post.link,
                                post_id=post_id,
                            )

                            translated_title = translate_text_into_english(title)

                            # by default if nothing change, language is english
                            source_language = None
                            # If the title changed we are checking the text language
                            # we do it after the translation because in case of text with a mix of languages,
                            # it can return the wrong one
                            if translated_title != title:
                                source_language = get_text_language(title)
                            else:
                                translated_title = None

                            post.title = title
                            post.translated_title = translated_title
                            post.source_language = source_language

                        if original_price and (not post.original_price or post.source.value == "not_reliable"):
                            # Override the title only if no title is yet defined or the source isn't navee_scraper
                            logger.info(
                                f"Update price: {post.original_price} -> {original_price}",
                                post_link=post.link,
                                post_id=post_id,
                            )

                            post.original_price = original_price
                            post.original_currency = original_currency
                            post.organisation_currency_price = organisation_currency_price
                            post.raw_price = price

                        if description and (not post.description or post.source.value == "not_reliable"):
                            # Override the description only if no description is yet defined or the source isn't navee_scraper
                            logger.info(
                                f"Update description: {post.description} -> {description}",
                                post_link=post.link,
                                post_id=post_id,
                            )

                            post.description = description

                        if poster and (not post.poster or post.source.value == "not_reliable"):
                            # Override the poster only if no poster is yet defined or the source isn't navee_scraper
                            logger.info(
                                f"Update poster: {post.poster} -> {poster}",
                                post_link=post.link,
                                post_id=post_id,
                            )

                            poster = poster_dao.get(post.website_id, name=poster, session=session)

                            if poster is None:
                                poster = poster_dao.add(
                                    name=poster,
                                    website_id=post.website_id,
                                    organisation_id=organisation_id,
                                    session=session,
                                )

                            post.poster = poster

            post_images = post.images

            # If there is no more image in the post, delete it
            if not post_images:
                session.delete(post)

            session.commit()

            # Update the takedown status depending on the information extraction results
            update_takedown_status_from_infex_results(post, post_images)

    else:

        logger.info(f"Running Infex on a new post: {post_body['post']['url']}", post_link=post_body["post"]["url"])

        with Session(post_body["organisation_name"]) as session:

            # Run the information extraction on a post before sending it to the insertion worker
            try:

                # Check that the environment name matches the current environment name
                environment_name = post_body["environment_name"]

                if environment_name != ENVIRONMENT_NAME:
                    print("Environment names do not match")
                    sentry_sdk.capture_message("Environment names do not match")
                    return

                item = post_body["post"]
                log_input = deepcopy(item)
                log_output = []

                post_url = item["url"]

                # We can't properly process the posts from websites which are not monitored
                domain_name = get_domain_name_from_url(post_url)
                website = session.query(Website).filter_by(domain_name=domain_name).first()

                if website and not website.can_monitor:
                    # The website is particularly difficult to access:
                    # pass on the post information to the Insertion Worker without running the information extraction
                    logger.info(f"The website is not monitored: {website.domain_name}", post_link=post_url)

                    send_task(post_body)
                    return

                scroll_smoothly = False

                if requires_scroll_smoothly(post_url):
                    scroll_smoothly = True

                # Build an object which will replace the pictures list in the post body
                # We need this because when iterating over items in a dict, we are manipulating copies
                new_pictures_list = []

                # Examine images
                for image_data in item["pictures"]:

                    # image_url is either a string (image_url) or a dict (keys image_url and duplicated_group_id)
                    # We systematically transform image_data into a dictionary
                    if isinstance(image_data, str):
                        image_data = {
                            "picture_url": image_data,
                            "s3_url": None,
                            "duplicated_group_id": None,
                        }

                    image_url = image_data["picture_url"]
                    s3_image_url = image_data.get("s3_url", image_url)

                    (
                        extracted_page_url,
                        title,
                        price,
                        description,
                        poster,
                        pattern_detected,
                        infex_error,
                    ) = infex_single_website(
                        post_url,
                        image_url,
                        s3_image_url,
                        scroll_smoothly=scroll_smoothly,
                        page_timeout_override=page_timeout_override,
                        element_timeout_override=element_timeout_override,
                        use_navee_driver=use_navee_driver,
                    )

                    logger.info(
                        "Output of extract_meta_information: "
                        f"{(extracted_page_url, title, price, description, poster, pattern_detected, infex_error)}",
                        post_link=post_url,
                        image_link=image_url,
                    )

                    # Add the information extraction results to the image data
                    image_data["information_extraction_results"] = {
                        "image_found": True if extracted_page_url else False,
                        "pattern_detected": True if pattern_detected else False,  # no None values if the infex ran
                        "price_detected": True if price else False,
                        "title_detected": True if title else False,
                        "execution_date": datetime.strftime(datetime.now(timezone.utc), "%Y-%m-%d-%H:%M:%S"),
                        "error": infex_error,
                    }

                    if extracted_page_url is not None:
                        if extracted_page_url != post_url:
                            # Most likely, the image contains a href linking to a product page

                            logger.info(
                                f"A page URL has been extracted and is different: {extracted_page_url}",
                                post_link=post_url,
                                image_link=image_url,
                            )

                            new_post_body = build_new_post_body_from_post_body(
                                post_body, image_data, extracted_page_url, title, price, description, poster
                            )

                            if send_insertion_tasks:
                                send_task(new_post_body)
                            else:
                                posts_to_insert.append(new_post_body)

                            log_output.append(new_post_body)

                        else:
                            logger.info(
                                f"Page extraction completed: {extracted_page_url}",
                                post_link=post_url,
                                image_link=image_url,
                            )
                            # Update the price and title if they are not already set
                            if not item.get("title"):
                                logger.info(f"Setting title: {title}")
                                item["title"] = title
                            if not item.get("price"):
                                logger.info(f"Setting price: {price}")
                                item["price"] = price

                            # Add image_data to current pictures list for current post_url
                            new_pictures_list.append(image_data)

                item["pictures"] = new_pictures_list
                post_body["post"] = item

                domain_name = get_domain_name_from_url(post_url)

                if item["pictures"]:
                    # If at least one image was not redirecting to a product page, send the post for insertion

                    logger.info(
                        f"Send the original post body with price '{item.get('price')}', title '{item.get('title')}, description '{item.get('description')}' and poster '{item.get('poster')}' to the insertion worker"
                        f" and {len(item['pictures'])} pictures",
                        post_link=post_url,
                    )

                    if send_insertion_tasks:
                        send_task(post_body)
                    else:
                        posts_to_insert.append(post_body)

                    log_output.append(post_body)

                session.add(
                    InfexLog(
                        url=post_url,
                        domain_name=domain_name,
                        payload=json.dumps(
                            {
                                "infex_log_version": 2,
                                "input": log_input,
                                "output": log_output,
                            }
                        ),
                    )
                )
                session.commit()

            except Exception as e:
                # If any exception occurs during the execution of the information extraction for a new post,
                # report it to Sentry and send the post body to the insertion worker
                logger.error(f"Exception during the information extraction of post: {post_url}", post_link=post_url)

                session.rollback()
                session.add(
                    InfexLog(
                        url=None,
                        domain_name=None,
                        payload=json.dumps(
                            {
                                "infex_log_version": 2,
                                "error": traceback.format_exc(),
                                "post_body": post_body,
                            }
                        ),
                    )
                )

                sentry_sdk.capture_exception(e)

                if send_insertion_tasks:
                    send_task(post_body)
                else:
                    posts_to_insert.append(post_body)

    if send_insertion_tasks:
        return
    else:
        return posts_to_insert


def build_new_post_body_from_post_body(post_body, image_data, extracted_page_url, title, price, description, poster):
    """
    Remove the image_data of interest from the post_body provided as an input for the information extraction worker
    and create a new post_body object corresponding to the parameters of this function
    (image_data, extracted_page_url, title, price)

    Parameters:
    ===========
    post_body: dict
        input of the insertion and information extraction workers
    image_data: dict
        contains the keys "picture_url", "s3_url", "duplicated_group_id" and "information_extraction_results"
    extracted_page_url: str
        URL of the new post to create
    title: str
    price: str

    Returns:
    ========
    new_post_body: input of the insertion and information extraction workers
    """

    # Remove image_data from post_body["post"]["pictures"]
    post_body["post"]["pictures"].remove(image_data)

    # Copy post_body to new_post_body
    new_post_body = copy.deepcopy(post_body)
    new_item = new_post_body["post"]

    # Update new_item["pictures"], new_item["url"], new_item["price"], new_item["title"]
    new_item["pictures"] = [image_data]
    new_item["url"] = extracted_page_url
    new_item["title"] = title
    new_item["price"] = price

    # Set poster, description and archive_link to None
    new_item["poster"] = poster
    new_item["description"] = description
    new_item["archive_link"] = None

    return new_post_body


def build_new_post_body_from_image_object(
    image, extracted_page_url, title, price, description, poster, pattern_detected
):
    """Create a post_body ready to be sent to the insertion worker from an image (database object)

    Parameters:
    ===========
    image: SQLAlchemy Image object
    extracted_page_url: str
    title: str
    price: str
    description: str
    poster: str
    pattern_detected: bool

    Returns:
    ========
    post_body: input of the insertion and information extraction workers
    """

    # Use the properties of the organisation associated to the existing image to determine which workers to enable
    organisation = image.post.organisation

    post_body = {
        "environment_name": ENVIRONMENT_NAME,
        "organisation_name": organisation.name,
        "search_in_rise": True,
        "launch_archiving": organisation.activate_archiving_feature,
        "launch_classifying": organisation.activate_post_category_classification_feature,
        "launch_logo_detection": organisation.activate_logo_detection_feature,
        "post": {
            "scraping_time": datetime.strftime(datetime.now(timezone.utc), "%Y-%m-%d-%H:%M:%S"),
            "poster": poster,
            "price": price,
            "url": extracted_page_url,
            "archive_link": None,
            "title": title,
            "pictures": [
                {
                    "picture_url": image.url,
                    "s3_url": image.s3_url,
                    "duplicated_group_id": image.duplicated_group_id,
                    "information_extraction_results": {
                        "image_found": True if extracted_page_url else False,
                        "pattern_detected": True if pattern_detected else False,
                        "price_detected": True if price else False,
                        "title_detected": True if title else False,
                        "execution_date": datetime.strftime(datetime.now(timezone.utc), "%Y-%m-%d-%H:%M:%S"),
                        "error": None,
                    },
                }
            ],
            "description": description,
            "source": "RISE",
            "post_label": None,
            "category": None,
            "payload": None,
        },
    }

    return post_body


def send_task(post):

    if not post["post"]["pictures"]:
        logger.info(f"Skipping post without images: {post['post']['url']}", post_link=post["post"]["url"])
        return

    if is_not_a_post_url(post['post']['url']):
        logger.info(f"Skipping post by url pattern blacklist: {post['post']['url']}", post_link=post["post"]["url"])
        return

    organisation = (
        post.get("organisation_id", None) if post.get("organisation_id", None) else post.get("organisation_name", None)
    )

    if not organisation:
        return

    with Session(organisation) as session:

        tracked_websites = [ws.domain_name for ws in session.query(SpecificScraperWebsite.domain_name).all()]

        # This way we cater to remove www.website.com, fr.website.com, mb.website.com
        domain_name = get_domain_name_from_url(post["post"]["url"])

        if domain_name in tracked_websites:
            logger.info(f"Sending post to recrawling: {post['post']['url']}", post_link=post["post"]["url"])

            # domain_name information is useful for the post_recrawling function in specific scraper.
            # specific scraper does not have the function and the exceptions that go with it to get domain name from url.
            post["domain_name"] = domain_name

            try:
                session.add(
                    InfexLog(
                        url=post["post"]["url"],
                        domain_name=domain_name,
                        payload=f"Sending crawling task to specific-scraper \n {json.dumps(post)}",
                    )
                )
                session.commit()
            except Exception:
                session.rollback()
            logger.info(
                "Sending new specific-scraper crawling task for the post",
                post_link=post["post"]["url"],
            )
            scraping_task = {
                "url": post["post"]["url"],
                "page_type": "POST",
                "domain_name": domain_name,
                "organisation_name": post.get("organisation_name"),
                "source": "RISE_RECRAWLING",
            }
            send_scraping_task(scraping_task)

        else:
            logger.info(f"Sending post to insertion worker: {post['post']['url']}", post_link=post["post"]["url"])
            send_insertion_task(post)


def check_pattern_for_webmonitor(post_id, organisation_id):
    """Check for patterns in the page to change post link if necessary

    Parameters
    ----------
    post_id: int
    """

    logger.info("processing post {}".format(post_id), post_id=post_id)

    with Session(organisation_id) as session:

        # If the key post_id is provided but the post is not found, a NoResultsFound error is raised by sqlalchemy
        post = (
            session.query(Post).filter_by(id=post_id).options(joinedload(Post.images), joinedload(Post.website)).one()
        )

        # We can't properly process the posts from websites which we can't monitor
        website = post.website
        if not website.can_monitor:
            return

        scroll_smoothly = False
        if requires_scroll_smoothly(post.link):
            logger.info("domain requires scrolling", post_id=post.id, post_link=post.link)
            scroll_smoothly = True

        for image in post.images:
            # we are only interested in pattern detection for web monitor
            (
                extracted_page_url,
                _,
                _,
                _,
                _,
                _,
                _,
            ) = infex_single_website(post.link, image.url, image.s3_url, scroll_smoothly=scroll_smoothly)

            if extracted_page_url is not None and extracted_page_url != post.link:
                logger.info("new page url found: {}".format(extracted_page_url), post_id=post.id, post_link=post.link)

                # check if posts with extracted_page_url already exists
                new_post = (
                    session.query(Post)
                    .filter(Post.link == extracted_page_url)
                    .filter(Post.organisation_id == post.organisation_id)
                    .first()
                )

                if new_post is not None:
                    # we assign image to new post_id
                    logger.info(
                        "image attached to existing post {}".format(new_post.id),
                        post_id=new_post.id,
                        post_link=new_post.link,
                    )
                    image.post_id = new_post.id
                else:
                    logger.info("image attached to new post")
                    # Create a post and assign image to it
                    domain_name = get_domain_name_from_url(extracted_page_url)

                    # Get website object
                    website = session.query(Website).filter_by(domain_name=domain_name).first()

                    # If website is not found in database, create it
                    if website is None:
                        website = Website(domain_name=domain_name)
                        session.add(website)

                    new_post = Post(
                        description="",
                        original_price=0.0,
                        original_currency="",
                        organisation_currency_price=0.0,
                        crawling_date=datetime.now(timezone.utc),
                        link=extracted_page_url,
                        poster=None,
                        website=website,
                        category=None,
                        organisation_id=post.organisation_id,
                        taken_down=False if website.can_monitor else None,
                    )

                    session.add(new_post)
                    image.post_id = new_post.id

        # If there is no more image in the post, delete it
        post_images = session.query(Image).filter_by(post_id=post.id).all()
        if not post_images:
            logger.info("delete old post", post_id=post.id, post_link=post.link)
            session.delete(post)

        session.commit()


if __name__ == "__main__":

    infex_body = {
        "environment_name": "production",
        "launch_archiving": False,
        "launch_classifying": False,
        "launch_logo_detection": False,
        "organisation_name": "Demo_Organisation",
        "post": {
            "pictures": [
                {
                    "duplicated_group_id": "69966323",
                    "picture_url": "https://cdn1.ozone.ru/s3/multimedia-z/6526018211.jpg",
                    "s3_url": "https://s3-eu-west-1.amazonaws.com/counterfeit-production-bucket/production/images/demo_organisation/b1c56b6f-4000-4320-9bc3-58f55134f75a.jpeg",
                }
            ],
            "scraping_time": "2023-04-07-14:08:29",
            "source": "RISE",
            "url": "https://www.ozon.ru/product/sumka-tout-valentino-834321137/",
        },
        "search_in_rise": False,
    }

    worker_information_extraction(infex_body, page_timeout_override=3, element_timeout_override=1)
