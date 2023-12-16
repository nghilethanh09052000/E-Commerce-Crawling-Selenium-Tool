from typing import Optional
import requests
import json
from app import logger
from app.models.marshmallow.config import ScrapeSchema
from app.service.api_scraping import field_retriever_modules
from app.helpers.utils import get_formatted_post_body


class ApiDriver:
    def __init__(self, domain_name: Optional[str] = None, config: Optional[ScrapeSchema] = None) -> None:
        self.domain_name = domain_name
        self.config = config

    def scrape_post(self, post_url):
        logger.info(f"Requesting post url {post_url}")
        request_details = self.config.post_information_retriever_module.api_request_params
        payload = request_details.post_body
        method_type = request_details.method_type
        api_headers = json.loads(request_details.api_headers) if request_details.api_headers else None

        response = requests.request(method_type, post_url, headers=api_headers, data=payload)

        return response.json()

    def search(self, search_url, query, max_posts_to_discover):
        logger.info(f"Requesting post url {search_url}")
        request_details = self.config.search_pages_browsing_module.api_request_params

        payload = get_formatted_post_body(request_details.post_body, query, max_posts_to_discover)

        method_type = request_details.method_type
        api_headers = json.loads(request_details.api_headers) if request_details.api_headers else None

        response = requests.request(method_type, search_url, headers=api_headers, data=payload)

        return response.json()

    def get_field_retriever_module_value(self, module_config, response, module_name=""):
        """
        Main function to call field retrieval and handle None Cases
        If Element is passed the field retrieval should be applied on the element instead of the main driver page
        """

        try:
            if module_config is None:
                return None
            field_retriever_module = getattr(field_retriever_modules, module_config.name)
            logger.info(f"\033[93m Fetching data from get_field_retriever_module_value for {module_name} \033[0m")
            if field_retriever_module is None:
                return None

            field = field_retriever_module(config=module_config, response=response)
            return field
        except Exception as ex:
            logger.info(f"\033[93m Error on get_field_retriever_module_value :{module_name} - Exception {str(ex)}")
            return None
