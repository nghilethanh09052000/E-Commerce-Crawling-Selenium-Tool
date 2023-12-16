from datetime import datetime, timezone
from app import logger
from app.models.proto.webpage_pb2 import ScrapingResult
from app.models.proto.logpage_pb2 import Logpage
from app.dao.logs import LogDAO
from app.dao import RedisDAO

log_dao = LogDAO()
redis_dao = RedisDAO()


def parse_log_page(scraping_result: ScrapingResult) -> Logpage():
    """Format Specific Scraper Response to Proto Class"""
    log_page = Logpage()
    # method to parse the log, can change later on to compressed webpage
    log_page.data_type = Logpage.LogDataType.ScrapingResult
    # to unparse use WEBPAGE_OBJ.ParseFromString(<string>)
    serialized_message = scraping_result.SerializeToString()
    log_page.data = serialized_message
    return log_page


def log_response(url, scraping_result: ScrapingResult):
    try:
        creation_date_timestamp = str(datetime.now(timezone.utc))
        # Parse the log
        log_page = parse_log_page(scraping_result)
        # Serialize to Binary String
        serialized_message = log_page.SerializeToString()
        # Save in Dynamo DB
        log_dao.add(url=url, creation_date_timestamp=creation_date_timestamp, payload=serialized_message)

        redis_dao.set_url_log(url=url, creation_date_timestamp=creation_date_timestamp)

    except Exception as ex:
        logger.error(f"Exception at logging response {str(ex)}")
