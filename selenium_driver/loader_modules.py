import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium_driver import logger
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    ElementNotVisibleException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium_driver.actions import find_element_and_click


def scroll_down_smoothly(selenium_driver):
    driver = selenium_driver.driver
    is_at_bottom = False
    time_scroll_action = 3
    scroll_tolerance_action = 100
    scroll_sleep = 0.1
    max_scroll = 20
    nb_scroll = 0
    while not is_at_bottom and nb_scroll < max_scroll:
        # Scroll down using down key during 3s
        endtime = time.time() + time_scroll_action
        while True:
            webdriver.ActionChains(driver).send_keys(Keys.DOWN).perform()
            time.sleep(scroll_sleep)
            if time.time() > endtime:
                break

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return window.pageYOffset")
        scroll_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height + driver.get_window_size()["height"] + scroll_tolerance_action > scroll_height:
            is_at_bottom = True

        nb_scroll += 1


def load_more_by_click(selenium_driver, config, action_before_search_pages_browsing_module=None):
    driver = selenium_driver.driver
    loading_delay = config.loading_delay
    scroll_down_before_click = config.scroll_down_before_click
    requires_url_update = config.requires_url_update
    css_selector = config.css_selector
    scroll_pause_time = config.scroll_pause_time
    previous_page = driver.current_url
    print("config", config, config.name)
    try:
        if scroll_down_before_click:
            # Scroll down to the bottom
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")

        if css_selector:
            is_clicked = find_element_and_click(driver, config)
            # Force updating the current page
            time.sleep(int(loading_delay))

            if not is_clicked:
                return False

        if scroll_pause_time:
            load_more_by_scrolling_module(selenium_driver, config, action_before_search_pages_browsing_module)

    except (
        NoSuchElementException,
        ElementClickInterceptedException,
        ElementNotInteractableException,
        ElementNotVisibleException,
        WebDriverException,
    ) as ex:
        logger.info(f"Exception on load_more_by_click {ex}")
        return False
    except TimeoutException:
        logger.info("TimeoutException on load_more_by_click")
        return True

    if requires_url_update:
        if previous_page == driver.current_url:
            return False
        else:
            return True


def go_to_next_page_module(selenium_driver, config, action_before_search_pages_browsing_module=None):
    """
    Config options:
        - css_selector (required): css selector to retrieve clickable next page button
    """
    driver = selenium_driver.driver
    css_selector = config.css_selector

    previous_page = driver.current_url

    try:
        next_page_element = driver.wait_and_find_element(By.CSS_SELECTOR, css_selector)
        href = next_page_element.get_attribute("href")
        if not href:
            logger.warn("next_page_element.get_attribute('href') returns nothing")
            return False
        selenium_driver.get(
            href,
            loading_delay=config.loading_delay,
            auto_kill_driver=config.restart_driver,
        )

        # # action before (usually click on something)
        if action_before_search_pages_browsing_module:
            selenium_driver.get_action_retriever_module_value(
                action_before_search_pages_browsing_module,
                "action_before_search_pages_browsing_module",
            )

        new_page = selenium_driver.driver.current_url
        logger.info(f"Accessing next page url : {new_page}")
    except NoSuchElementException:
        logger.warn("NoSuchElementException on go_to_next_page_module")
        return False
    except TimeoutException:
        logger.warn("TimeoutException on go_to_next_page_module")
        return True
    except Exception as ex:
        logger.warn(f"Other Exceptions on go_to_next_page_module {str(ex)}")
        return False

    if new_page == previous_page:
        return False
    else:
        return True


def load_more_by_scrolling_module(selenium_driver, config, action_before_search_pages_browsing_module=None):
    """
    Config options:
        - scroll_pause_time (optional): pause time after each scroll
    """

    driver = selenium_driver.driver
    scroll_pause_time = config.scroll_pause_time
    scroll_range = config.scroll_range
    fixed_scroll_to = config.fixed_scroll_to
    scroll_up = config.scroll_up

    # if selector in config try go to next page link
    css_selector = config.css_selector

    previous_height = driver.execute_script("return document.body.scrollHeight")

    # try 10 times to scroll down
    for i in range(scroll_range):
        scroll_to = "document.documentElement.scrollHeight"

        if fixed_scroll_to:
            page_yoffset = driver.execute_script("return window.pageYOffset")
            scroll_to = page_yoffset + fixed_scroll_to

        if scroll_up:
            # Scroll up to the top
            driver.execute_script("window.scrollTo(0, 0);")
        else:
            # Scroll down to the bottom
            driver.execute_script(f"window.scrollTo(0, {scroll_to});")

        # Wait to load page
        time.sleep(float(scroll_pause_time))

    if fixed_scroll_to:
        page_yoffset = driver.execute_script("return window.pageYOffset")
        page_innerHeight = driver.execute_script("return window.innerHeight")
        new_height = driver.execute_script("return document.body.scrollHeight") - 2
        ## if there is still a place to load
        if new_height > (page_innerHeight + page_yoffset):
            return True
    else:
        # Check whether we have indeed scrolled down
        new_height = driver.execute_script("return document.body.scrollHeight")

        if previous_height < new_height:
            return True

    # After scrolling if link to next page is present, like load_more_by_click
    if css_selector:
        try:
            next_page_element = driver.wait_and_find_element(By.CSS_SELECTOR, css_selector)
            if next_page_element.get_attribute("href"):
                selenium_driver.get(
                    next_page_element.get_attribute("href"),
                    loading_delay=config.loading_delay,
                )
                # # action before (usually click on something)
                if action_before_search_pages_browsing_module:
                    selenium_driver.get_action_retriever_module_value(
                        action_before_search_pages_browsing_module,
                        "action_before_search_pages_browsing_module",
                    )
                return True
            else:
                return False
        except NoSuchElementException:
            logger.info("NoSuchElementException on load_more_by_scrolling_module")
            return False
        except TimeoutException:
            logger.info("TimeoutException on load_more_by_scrolling_module")
            return False
        except Exception as ex:
            logger.info(f"Other Exceptions on load_more_by_scrolling_module {str(ex)}")
            return False

    # if after 10 scroll, no progress in scrolling, return False
    return False


def click_on_next_page_module(selenium_driver, config, action_before_search_pages_browsing_module=None):
    """
    Config options:
        - loading_delay (optional): pause time after each action
    """

    driver = selenium_driver.driver
    loading_delay = config.loading_delay
    scroll_down_before_click = config.scroll_down_before_click

    previous_page = driver.current_url

    try:
        if scroll_down_before_click:
            load_more = True
            while load_more:
                load_more = load_more_by_scrolling_module(
                    selenium_driver, config, action_before_search_pages_browsing_module
                )

        is_clicked = find_element_and_click(driver, config)

        if not is_clicked:
            return False

        # Force updating the current page
        time.sleep(loading_delay)

        # # action before (usually click on something)
        if action_before_search_pages_browsing_module:
            selenium_driver.get_action_retriever_module_value(
                action_before_search_pages_browsing_module,
                "action_before_search_pages_browsing_module",
            )

    except (
        NoSuchElementException,
        ElementClickInterceptedException,
        ElementNotInteractableException,
        ElementNotVisibleException,
        WebDriverException,
    ) as ex:
        logger.warn(f"Exception on click_on_next_page_module {ex}")
        return False
    except TimeoutException:
        logger.warn("TimeoutException on click_on_next_page_module")
        return True

    new_page = driver.current_url
    if new_page == previous_page:
        return False
    else:
        return True


def load_more_by_scrolling_one_scroll_at_a_time(
    selenium_driver, config, action_before_search_pages_browsing_module=None
):
    """
    Scrolls slowly and retrieve results, works well for websites that load content on scroll only
    Config options:
        - scroll_range
        - scroll_pause_time (optional): pause time after each scroll
        - loading_delay (optional): time to wait after scrolling
        - css_selector (optional): element to click after scrolling if and when encountered and clickable.
    """
    driver = selenium_driver.driver
    scroll_pause_time = config.scroll_pause_time
    scroll_range = config.scroll_range
    loading_delay = config.loading_delay
    css_selector = config.css_selector

    previous_height = driver.execute_script("return document.body.scrollHeight")
    print(f"previous: {previous_height}")

    # try 10 times to scroll down
    for i in range(scroll_range):
        page_yoffset = driver.execute_script("return window.pageYOffset")
        # Scroll down by last element height
        driver.execute_script(f"window.scrollTo(0, {page_yoffset+1000})")

        # Wait to load page
        time.sleep(float(scroll_pause_time))
    time.sleep(float(loading_delay))

    page_yoffset = driver.execute_script("return window.pageYOffset")
    page_innerHeight = driver.execute_script("return window.innerHeight")
    new_height = driver.execute_script("return document.body.scrollHeight") - 2
    # Click load_more button if encountered after scrolling.
    if css_selector:
        try:
            find_element_and_click(driver, config)
            time.sleep(float(loading_delay))
            return True
        except Exception as e:
            logger.info(f"Exception on clicking element. Exception:{e}")
            pass
    ## if there is still a place to load
    if new_height > (page_innerHeight + page_yoffset):
        return True

    return False
