from google.protobuf.json_format import MessageToJson
from datetime import datetime, timezone
from app import logger
from app.models.enums import UrlPageType

from app.models.proto.webpage_pb2 import (
    Webpage,
    StructuredPostData,
    Image,
    StructuredPosterData,
    OutgoingLink,
    LinkContext,
    WebhostInfo,
    ScrapingResult,
)


def parse_response_to_proto(response: dict):
    scraping_result = ScrapingResult()

    # ad page details
    web_page = parse_webpage(response)
    scraping_result.pages.append(web_page)

    # hosting page
    hostinpage = parse_hostingpage(response)
    scraping_result.hosts.append(hostinpage)

    # errors
    if "errors" in response:
        scraping_result.errors.extend(response["errors"])

    # successful
    scraping_result.successful = response.get("successful", True)

    ## TODO: the api will next contain the option of returning json or message class as response.
    # Convert protobuf class to json for the api response
    json_scraping_result = MessageToJson(scraping_result, including_default_value_fields=True)
    return scraping_result, json_scraping_result


def parse_hostingpage(response: dict) -> WebhostInfo():
    logger.info("Parsing Response to WebhostInfo")

    web_host_info = WebhostInfo()

    if response.get("who_is_information"):
        web_host_info.who_is.update(response.get("who_is_information"))

    if response.get("web_stack_information"):
        web_host_info.web_stack.update(response.get("web_stack_information"))
    return web_host_info


def parse_webpage(response: dict) -> Webpage():
    """Parse scraper module response to Protobuf class Webpage"""
    logger.info("Parsing Response to Webpage")

    web_page = Webpage()

    web_page.url = response.get("url")
    web_page.creation_date_timestamp = str(datetime.now(timezone.utc))
    if response.get("s3_content_url"):
        web_page.s3_content_url = response.get("s3_content_url")

    if response.get("s3_archive_url"):
        web_page.s3_archive_url = response.get("s3_archive_url")

    if response.get("title"):
        web_page.title = response.get("title")

    if response.get("translated_title"):
        web_page.translated_title = response.get("translated_title")

    if response.get("description"):
        web_page.description = response.get("description")

    if response.get("translated_description"):
        web_page.translated_description = response.get("translated_description")

    if response.get("source_language"):
        web_page.source_language = response.get("source_language")

    if response.get("source_language"):
        web_page.source_language = "source_language"

    for outgoing_link in response.get("outgoing_links", []):
        link_data = OutgoingLink()
        link_data.to_url = outgoing_link.get("url")
        link_context = LinkContext()
        link_context.payload.update(outgoing_link)

        for image in outgoing_link.get("pictures", []):
            link_image = Image()
            link_image.image_url = image.get("picture_url")
            if image.get("s3_url"):
                link_image.s3_url = image.get("s3_url")
            link_context.images.append(link_image)

        link_data.context.CopyFrom(link_context)
        web_page.outgoing_links.append(link_data)

    if response.get("data"):
        if response["data"]["type"] == UrlPageType.POST.name:
            post_data = StructuredPostData()
            if response["data"].get("title"):
                post_data.title = response["data"].get("title")
            if response["data"].get("description"):
                post_data.description = response["data"].get("description")
            if response["data"].get("price"):
                post_data.price = response["data"].get("price")
            if response["data"].get("poster_name"):
                post_data.poster_name = response["data"].get("vendor")
            if response["data"].get("poster_link"):
                post_data.poster_link = response["data"].get("poster_link")
            post_data.payload.update(response["data"])
            images = response["data"].get("pictures")
            if images:
                for image in images:
                    post_image = Image()
                    post_image.image_url = image.get("picture_url")
                    if image.get("s3_url"):
                        post_image.s3_url = image.get("s3_url")
                    post_data.images.append(post_image)

            web_page.post.append(post_data)

        elif response["data"]["type"] == UrlPageType.POSTER.name:
            poster_data = StructuredPosterData()
            poster_data.name = response["data"].get("name")
            poster_data.description = response["data"].get("description")
            poster_data.translated_description = response["data"].get("translated_description")
            poster_data.profile_pic_url = response["data"].get("profile_pic_url")
            poster_data.payload = response["data"]

            web_page.poster.append(poster_data)

    logger.info("Parsing Response Completed")
    return web_page
