import os
import yaml

import hiyapyco

from app.models.marshmallow.config import ScrapeSchema
from app.dao import ChromeprofileDAO

chromeprofile_DAO = ChromeprofileDAO()


def load_domain_config(config_file) -> ScrapeSchema:

    if not os.path.isfile(f"app/configs/yaml/{config_file}.yaml"):
        print(f"Config File {config_file} doesn't exist resorting to default")
        config_file = "default"

    with open(f"app/configs/yaml/{config_file}.yaml", "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)

    # Include inheritance to main .yaml file
    filename_to_include = config.get("include", None)

    if filename_to_include:
        config = hiyapyco.load(
            f"app/configs/yaml/{filename_to_include}",
            f"app/configs/yaml/{config_file}.yaml",
            method=hiyapyco.METHOD_SUBSTITUTE,  # Replace lists instead of merging
            usedefaultyamlloader=True,
        )

    return ScrapeSchema().load(config["framework"])


def load_config(config_file, load_chrome_profile=True) -> ScrapeSchema:
    config = load_domain_config(config_file)

    # Override Configuration to cater for Rotating Proxy Requirements
    if config.driver_initialization_module is not None:

        if config.proxies:
            config.driver_initialization_module.headless = False
            config.driver_initialization_module.xvfb = True
            config.driver_initialization_module.undetected_driver = True

        if load_chrome_profile is True and config.driver_initialization_module.chromeprofile_domain_name:
            chromeprofile_name = chromeprofile_DAO.get_available_chromeprofile(
                config.driver_initialization_module.chromeprofile_domain_name
            )
            config.driver_initialization_module.chromeprofile_name = chromeprofile_name

    # Use this field in search module , for search only based scraping
    if config.search_pages_browsing_module is not None:

        if config.search_pages_browsing_module.post_url_template is None:
            config.search_pages_browsing_module.post_url_template = (
                config.post_information_retriever_module.post_url_template
            )

    return config
