from app.models.marshmallow.config import LoginModule
from selenium_driver.main_driver import Selenium


def login(selenium_driver: Selenium, config: LoginModule):
    selenium_driver.login(
        login_page_url=config.login_page_url,
        username_css_selector=config.username_css_selector,
        password_css_selector=config.password_css_selector,
        username=config.username,
        password=config.password,
        submit_css_selector=config.submit_css_selector,
        cookies_css_selector=config.cookies_css_selector,
    )
