import base64
import json
import os
import random
import re
import time
from os import kill
from pathlib import Path
from signal import SIGKILL
from time import sleep
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlparse

import psutil
import requests
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from app.settings import GET_IP_URL
from app.configs.utils import load_config
from app.dao import ScrapingAttemptDAO, WebsiteDAO
from app.helpers.utils import clean_url
from app.models import ScrapingAttempt
from app.models.enums import RequestResult
from app.models.marshmallow.config import ScrapeSchema
from selenium_driver import actions as actions_modules
from selenium_driver import field_retriever_modules, logger
from selenium_driver.archiving.webshot_module import take_webshot
from selenium_driver.driver_wrapper import WrappedUndetectedChrome, WrappedWebdriverChrome
from selenium_driver.helpers.proxy import ProxyException, get_proxy_authentification_extension
from selenium_driver.helpers.s3 import download_folder_from_s3
from selenium_driver.helpers.utils import save_html
from selenium_driver.loader_modules import scroll_down_smoothly
from selenium_driver.settings import (
    CHROME_VERSION,
    DISABLE_XVFB,
    SPECIFIC_SCRAPER_AWS_BUCKET,
    sentry_sdk,
    DEFAULT_GET_PAGE_TIMEOUT,
)

scraping_attempt_DAO = ScrapingAttemptDAO()
website_DAO = WebsiteDAO()


class SeleniumException(Exception):
    pass


class Selenium:
    def __init__(self, domain_name: Optional[str] = None, config: Optional[ScrapeSchema] = None) -> None:
        self.driver = None
        self.vdisplay = None
        self.domain_name = domain_name
        self.config = config

        ## other functions
        self.take_screenshot = False
        self.take_screenshots = False

        # Load domain config if available, otherwise load default
        if self.config is None:
            self.config = load_config(config_file=domain_name)

        if domain_name:
            self.website = website_DAO.get(domain_name=self.domain_name)
        else:
            self.website = None

        self.proxy_provider = None
        self.proxy_country = None
        self.ip_address = None

    def _set_chrome_settings(self):
        # Launch a Chrome web driver
        if not self.config.driver_initialization_module.undetected_driver:
            chrome_options = webdriver.ChromeOptions()
        else:
            logger.info("Using undetected_chromedriver")
            # Use only as last resort, when all other flags fail to bypass Captcha/Bot Detection
            chrome_options = uc.ChromeOptions()

        # disable the loading of external resources and prevent network requests
        if self.config.driver_initialization_module.load_offline_driver:
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-extensions")

        # if not self.config.driver_initialization_module.undetected_driver:
        chrome_options.add_argument("--no-sandbox")

        # Issue with too small /dev/shm size in Docker containers
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--ignore-certificate-errors")

        # Mute Audio
        chrome_options.add_argument("--mute-audio")

        # to avoid issues with taking screenshots
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--force-device-scale-factor=1")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-browser-side-navigation")

        if not self.config.driver_initialization_module.load_images:
            logger.info("Not loading images in Chrome to use less resources")
            prefs = {"profile.managed_default_content_settings.images": 2}
            chrome_options.add_experimental_option("prefs", prefs)

        if self.config.driver_initialization_module.start_maximized:
            chrome_options.add_argument("--start-maximized")

        # Run headless
        if self.config.driver_initialization_module.headless and not self.config.driver_initialization_module.xvfb:
            chrome_options.add_argument("--headless")

        # Disable notifications from broswer
        chrome_options.add_argument("--disable-notifications")
        # Pass the argument 1 to allow and 2 to block broswer notifications (ex: allow mic/notifications/cam etc)
        chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.notifications": 2})

        if self.config.driver_initialization_module.chromeprofile_domain_name:
            chrome_profile_path = f"{os.path.abspath(os.getcwd())}/scraper/chromeprofiles/{self.config.driver_initialization_module.chromeprofile_name}"
            s3_file_name = f"chromeprofiles/{self.config.driver_initialization_module.chromeprofile_name}"

            logger.info(f"Using chrome profile: {chrome_profile_path}")

            if not Path(chrome_profile_path).is_dir():
                # load profiles from s3 bucket
                download_folder_from_s3(
                    bucket_name=SPECIFIC_SCRAPER_AWS_BUCKET,
                    object_key=s3_file_name,
                    file_path="./selenium_driver/",
                )

            chrome_options.add_argument(f"--user-data-dir={chrome_profile_path}")

        if self.config.driver_initialization_module.mobile_driver:
            logger.info("Using mobile driver")
            chrome_options.add_experimental_option(
                "mobileEmulation",
                {
                    "deviceMetrics": {"width": 375, "height": 812, "pixelRatio": 3.0},
                    "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19",
                },
            )

        if self.config.proxies:
            proxy = random.choice(self.config.proxies)

            # get settings to add to chrome options
            (
                proxy_authentification_extension,
                self.proxy_provider,
                self.proxy_country,
            ) = get_proxy_authentification_extension(
                proxy_name=proxy.name,
                proxy_country=proxy.country,
            )
            chrome_options.add_argument(f"--load-extension={proxy_authentification_extension}")

        elif self.config.driver_initialization_module.use_tor_proxy:
            logger.info("Launching Tor as a background process")
            os.system("nohup tor &")

            # Use Tor as a proxy (port 9150 if running locally with Tor Browser)
            chrome_options.add_argument("--proxy-server=socks5://127.0.0.1:9050")

        # Capabilities
        capabilities = DesiredCapabilities.CHROME
        capabilities["unhandledPromptBehavior"] = "dismiss"  # for alerts https://w3c.github.io/webdriver/#dfn-dismissed
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # for network logs

        if self.config.driver_initialization_module.page_load_strategy:  # interactive
            capabilities["pageLoadStrategy"] = self.config.driver_initialization_module.page_load_strategy

        logger.info(f"Using chrome options: {str(chrome_options.__dict__)}")
        return chrome_options, capabilities

    def get(
        self,
        url: str,
        loading_delay: float = None,
        auto_kill_driver: bool = False,
        attempts: int = 1,
        offline_driver=False,
    ) -> ScrapingAttempt:
        # kill the driver if autokill is set to true or if using rotating proxy to ensure a new session is created
        if self.driver is not None and (auto_kill_driver is True or self.config.proxies):
            self.kill_driver()

        if self.driver is None:
            self.launch_driver()

        if self.driver is None:
            return False

        # We cannot scrape those that need api framework for to avoid empty screenshots
        if self.config.name == "api_framework":
            logger.info("Disabling Driver Get for API Framework Domains")
            return False

        try:
            if self.config.proxies and not offline_driver:
                self.driver.get(GET_IP_URL)
                self.ip_address = self.driver.wait_and_find_element(By.TAG_NAME, "body").text

                logger.info(f"IP address: {self.ip_address}")

                if "This site can’t be reached" in self.ip_address:
                    logger.error(f"Proxy {self.proxy_provider} is not working")
                    raise ProxyException(f"Proxy {self.proxy_provider} is not working")

            if self.config.driver_initialization_module.cloudflare_bypass:
                self.driver.switch_to.new_window("tab")
                time.sleep(int(self.config.driver_initialization_module.cloudflare_bypass_time))

            self.driver.get(url)
            time.sleep(int(self.config.driver_initialization_module.loading_delay))

            body = self.driver.wait_and_find_element(By.TAG_NAME, "body").text
            if "This site can’t be reached" in body:
                if self.proxy_provider:
                    logger.error(f"Proxy {self.proxy_provider} is not working")
                    raise ProxyException(f"Proxy {self.proxy_provider} is not working")
                else:
                    logger.error("Network issues: This site can't be reached")
                    raise WebDriverException("Network issues: This site can't be reached")

            request_result = RequestResult.SUCCESS
            error_message = None

        except WebDriverException as e:
            # Handle get retries at least once in case of proxy failure or others
            logger.info(f"Error on driver GET {repr(e)}")

            if type(e) != ProxyException:
                sentry_sdk.capture_exception(e)

            request_result = RequestResult.PROXY_FAILURE if type(e) == ProxyException else RequestResult.DRIVER_FAILURE
            error_message = str(e)

        except Exception as e:
            logger.info(f"Unexpected error on driver GET {repr(e)}")
            sentry_sdk.capture_exception(e)
            request_result = RequestResult.OTHER_FAILURE
            error_message = repr(e)

        if offline_driver:
            return None

        if request_result == RequestResult.SUCCESS:
            # delays and resizing should happen before the screenshot below
            if loading_delay:
                time.sleep(loading_delay)

            if self.config.driver_initialization_module.start_maximized:
                self.driver.set_window_size(1280, 1024)

        screenshot = self.take_webshot()

        # we log attempts for both successes and failures
        scraping_attempt = scraping_attempt_DAO.create(
            url=url,
            page_title=self.driver.title,
            screenshot=screenshot,
            website_id=self.website.id if self.website else None,
            proxy_provider=self.proxy_provider,
            proxy_country=self.proxy_country,
            proxy_ip=self.ip_address,
            request_result=request_result,
            error_message=error_message,
        )

        if request_result in [RequestResult.DRIVER_FAILURE, RequestResult.PROXY_FAILURE] and attempts < 3:
            # Chrome crashed upon launching a new webdriver
            # Try to relaunch a driver after 10 seconds
            sleep(10)
            logger.info(f"Relaunching driver after {attempts} attempts")
            return self.get(url=url, loading_delay=loading_delay, auto_kill_driver=True, attempts=(attempts + 1))

        if request_result != RequestResult.SUCCESS:
            # The caller shouldn't bother with checking for "success".
            # Let's raise an error instead, can't forget to handle this one.
            logger.error(f"Selenium.get() failed with {request_result}: {error_message}")
            raise SeleniumException(f"Selenium.get() failed with {request_result}: {error_message}")

        return scraping_attempt

    def launch_driver(self):
        # We cannot scrape those that need api framework for to avoid empty screenshots
        if self.config.name == "api_framework":
            logger.info("Disabling Driver Get for API Framework Domains")
            return None

        logger.info("Launching Driver")
        ## get chrome options
        chrome_options, chrome_capabilities = self._set_chrome_settings()

        if self.config.driver_initialization_module.xvfb and not DISABLE_XVFB:
            logger.info("Enabling XVFB")
            from xvfbwrapper import Xvfb

            self.vdisplay = Xvfb()
            self.vdisplay.start()

        try:
            if self.config.driver_initialization_module.undetected_driver:
                self.driver = WrappedUndetectedChrome(
                    version_main=CHROME_VERSION,
                    options=chrome_options,
                    desired_capabilities=chrome_capabilities,
                    browser_executable_path="/opt/google/chrome/chrome",
                )
            else:
                self.driver = WrappedWebdriverChrome(
                    options=chrome_options,
                    desired_capabilities=chrome_capabilities,
                )

        except (WebDriverException, URLError) as e:
            logger.info(f"Error on driver initialization {str(e)}")
            # Chrome crashed upon launching a new webdriver
            # Try to relaunch a driver after 10 seconds
            sleep(10)
            self.kill_driver()
            try:
                # Get new chrome options and settings
                chrome_options, chrome_capabilities = self._set_chrome_settings()
                if self.config.driver_initialization_module.undetected_driver:
                    self.driver = WrappedUndetectedChrome(
                        version_main=CHROME_VERSION,
                        options=chrome_options,
                        desired_capabilities=chrome_capabilities,
                        browser_executable_path="/opt/google/chrome/chrome",
                    )
                else:
                    self.driver = WrappedWebdriverChrome(
                        options=chrome_options,
                        desired_capabilities=chrome_capabilities,
                    )
            except WebDriverException as relaunching_exception:
                # Relaunching a driver failed - report an exception to Sentry
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("error-type", "webdriver-relaunching-failed")
                    scope.set_extra("exception-message", relaunching_exception)
                    sentry_sdk.capture_message(
                        "Webdriver unsuccessfully relaunched 10 seconds after a Chrome crash upon initialization"
                    )

            # Relaunching a driver succeeded - report a message to Sentry
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("error-type", "webdriver-relaunching-succeeded")
                scope.set_extra("exception-message", e)
                sentry_sdk.capture_message(
                    "Webdriver successfully relaunched 10 seconds after a Chrome crash upon initialization"
                )

        if self.driver is None:
            return None

        if self.config.driver_initialization_module.start_maximized:
            self.driver.set_window_size(1280, 1024)

        if self.config.driver_initialization_module.override_user_agent:
            # remove headless from user agent to skip identification as scraper
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            user_agent = user_agent.replace("Headless", "")
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})

        if self.config.driver_initialization_module.cookies:
            cookies_url = self.config.driver_initialization_module.cookies.get("url")
            cookies_domain = urlparse(cookies_url).netloc
            self.driver.get(cookies_url)
            for name, value in self.config.driver_initialization_module.cookies.get("properties").items():
                self.driver.add_cookie({"name": name, "domain": cookies_domain, "value": value})

        if self.config.driver_initialization_module.driver_timeout:
            self.driver.set_page_load_timeout(int(self.config.driver_initialization_module.driver_timeout))
        else:
            self.driver.set_page_load_timeout(DEFAULT_GET_PAGE_TIMEOUT)

        return self.driver

    def get_driver_process_id(self):
        """Get the process ID"""
        try:
            return self.driver.service.process.pid
        except Exception as ex:
            logger.info(f"Exception at getting chrome process ID {str(ex)}")
            sentry_sdk.capture_exception(ex)
            return None

    def kill_driver(self):
        logger.info("Killing Driver")

        try:
            if self.driver:
                process_id = self.get_driver_process_id()
                self.driver.close()
                self.driver.quit()
                self.driver = None

                # Disable the killing procss for time being
                if process_id is not None:
                    self.kill_process(process_id)

            if self.vdisplay:
                self.vdisplay.stop()
                self.vdisplay = None
        except Exception as ex:
            logger.error(f"Exception at killing driver {repr(ex)}")
            self.driver = None
            self.vdisplay = None

    def kill_process(self, process_id):
        try:
            if psutil.pid_exists(process_id):
                logger.info("Process still exists will kill it")
                kill(process_id, SIGKILL)
            else:
                logger.info(f"Process {process_id} no longer exists")
        except Exception as ex:
            logger.info(f"Exception at killing process {str(ex)}")
            sentry_sdk.capture_exception(ex)

    def reload_driver(self):
        self.kill_driver()
        return self.launch_driver()

    def get_field_value(self, field):
        return ""

    def get_image_url(self, field):
        return ""

    def get_page_title(self):
        """Returns the web page title if it exists"""
        # # TODO: Check if the title changes by javascript if its caught here *
        try:
            return self.driver.title
        except Exception as ex:
            print(str(ex))
            pass

        return None

    def get_page_metadata(self, specific_key=None):
        """
        page_source - Page Data loaded in beautfiul soup
        """
        try:
            data = {}
            # head/meta should normally be loaded by now
            for tag in self.driver.wait_and_find_elements(By.TAG_NAME, "meta", timeout=1.0):
                if tag.get_attribute("name"):
                    data[tag.get_attribute("name")] = tag.get_attribute("content")
            if specific_key:
                return data.get(specific_key, None)
            return data
        except Exception as ex:
            logger.info(f"Error Processing get_domain_meta_data {repr(ex)}")
            return None

    def get_page_links(self):
        """Returns all the href available in the page"""

        page_links = dict()
        try:
            links = self.driver.wait_and_find_elements(By.TAG_NAME, "a")
            # traverse list
            for link in links:
                if link.get_attribute("href"):
                    # get_attribute() to get all href
                    page_links[link.get_attribute("href")] = {}

        except Exception as ex:
            logger.info(f"Error Processing get_page_links {repr(ex)}")
            pass

        return page_links

    def get_page_source(self):
        if self.driver is not None:
            return save_html(self.driver.execute_script("return document.documentElement.outerHTML;"))
        return None

    def take_webshot(self, url: str = None, kill_driver: bool = None):
        return take_webshot(selenium_driver=self, url=url, kill_driver=kill_driver)

    def get_alternate_links(self):
        """Returns all the related links in the page"""
        alternate_links = []

        try:
            # Get Canonical Link
            canonical_link_element = self.driver.find_element(By.CSS_SELECTOR, 'link[rel="canonical"]')

            # Get the value of the "href" attribute, which contains the canonical URL
            canonical_link = canonical_link_element.get_attribute("href")
            if canonical_link:
                alternate_links.append(canonical_link)

        except Exception as ex:
            logger.info(f"Error Processing get_alternate_links {repr(ex)}")
            pass

        try:
            # Get Alternate Link with hreflang to get different languages aswell
            alternates = self.driver.find_elements(By.CSS_SELECTOR, 'link[hreflang][rel="alternate"]')

            # Get the value of the "href" attribute, which contains the canonical URL
            for alternate in alternates:
                href = alternate.get_attribute("href")
                if href:
                    alternate_links.append(href)

        except Exception as ex:
            logger.info(f"Error Processing get_alternate_links {repr(ex)}")
            pass

        return alternate_links

    def update_rotating_proxy_ip(self, proxy_change_ip):
        """Calling this request updates the IP Being used"""
        requests.get(proxy_change_ip)

    def get_field_retriever_module_value(self, module_config, module_name="", element=None):
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

            field = field_retriever_module(self.driver, module_config, element)
            return field
        except Exception as ex:
            logger.info(f"\033[93m Error on get_field_retriever_module_value :{module_name} - Exception {str(ex)}")
            return None

    def get_action_retriever_module_value(self, module_config, module_name=""):
        """Main function to call field retrieval and handle None Cases"""
        if module_config is None:
            return None

        for action_config in module_config:
            try:
                action_module = getattr(actions_modules, action_config.name)
                logger.info(f"\033[93m Fetching data from get_action_retriever_module_value for {module_name} \033[0m")
                if action_module is None:
                    logger.info(
                        f"\033[93m Error on get_action_retriever_module_value {module_name}. Module does not exist. \033"
                    )
                    continue
                action_module(self.driver, action_config)
            except Exception as ex:
                logger.info(f"\033[93m Error on get_action_retriever_module_value :{module_name} - Exception {str(ex)}")
                pass
        return

    def scroll_down_smoothly(self):
        scroll_down_smoothly(self)

    def login(
        self,
        login_page_url,
        username_css_selector,
        password_css_selector,
        username,
        password,
        submit_css_selector,
        cookies_css_selector=None,
    ):
        self.get(login_page_url)

        if cookies_css_selector:
            # Search for the cookies message and click on it if present
            time.sleep(2)
            try:
                self.driver.wait_and_find_element_and_click(By.CSS_SELECTOR, cookies_css_selector, timeout=2.0)
            except Exception as e:
                logger.info(f"Ignoring exception in login/accept_cookies: {repr(e)}")
                pass

        username_object = self.driver.wait_and_find_element(By.CSS_SELECTOR, username_css_selector)
        username_object.send_keys(username)
        time.sleep(2)

        password_object = self.driver.wait_and_find_element(By.CSS_SELECTOR, password_css_selector)
        password_object.send_keys(password)
        time.sleep(2)

        self.driver.wait_and_find_element_and_click(By.CSS_SELECTOR, submit_css_selector)
        time.sleep(2)

    def get_request_id_for_url(self, url: str) -> Optional[str]:
        try:
            logs = self.driver.get_log("performance")
            for i in logs:
                log = json.loads(i.get("message", {})).get("message", {})
                if log.get("params", {}).get("response", {}).get("url", "") == url:
                    return log.get("params", {}).get("requestId")
        except Exception as e:
            logger.info(f"Error on get_request_id_for_urls {str(e)}")
            sentry_sdk.capture_exception(e)

    def get_img_bytes_from_request_id(self, request_id: str) -> bytes:
        response = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
        base64_message = response["body"]
        return base64.b64decode(base64_message)

    def get_post_identifier(self, item, config):
        regex = config.regex
        regex_substitute = config.regex_substitute
        attribute_name = config.attribute_name

        if attribute_name:
            url = item.get_attribute(attribute_name)
        else:
            url = item.get_attribute("href")

        url = clean_url(url, config.post_url_cleaning_module)

        if regex_substitute:
            regex_substitute_string = config.regex_substitute_string if config.regex_substitute_string else ""
            url = re.sub(regex_substitute, regex_substitute_string, url)

        if regex:
            if re.search(regex, str(url)):
                url = re.search(regex, str(url)).group(1)
            else:
                return None
        return url
