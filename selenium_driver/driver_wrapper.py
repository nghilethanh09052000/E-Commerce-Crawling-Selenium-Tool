import os

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.remote_connection import RemoteConnection
import undetected_chromedriver as uc
from undetected_chromedriver.patcher import Patcher

from selenium_driver import logger
from selenium_driver.settings import DEFAULT_REQUIRED_LOADING_TIMEOUT, MAX_GET_PAGE_TIMEOUT


RemoteConnection.set_timeout(MAX_GET_PAGE_TIMEOUT)  # Will lose the connection to the browser after this time


def wait_and_find_element(driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None):
    root = root_element if root_element else driver
    return WebDriverWait(root, float(timeout)).until(EC.presence_of_element_located((by, value)))


def wait_and_find_element_visible(driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None):
    root = root_element if root_element else driver
    return WebDriverWait(root, float(timeout)).until(EC.visibility_of_element_located((by, value)))


def wait_and_find_element_clickable(driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None):
    root = root_element if root_element else driver
    node = wait_and_find_element(root, by, value, timeout)
    # NB In theory element_to_be_clickable below should scroll automatically to the element making
    # an explicit move_to_element unnecessary. However, it could be possible that some elements
    # become clickable only when hovered-on, and it's not clear if element_to_be_clickable is
    # enough in such cases. TODO Run some experiments with this.
    ActionChains(driver).move_to_element(node).pause(0.1).perform()
    return WebDriverWait(root, float(timeout)).until(EC.element_to_be_clickable((by, value)))


def wait_and_find_elements(driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None):
    root = root_element if root_element else driver
    try:
        WebDriverWait(root, float(timeout)).until(EC.presence_of_all_elements_located((by, value)))
    except Exception as e:
        logger.info(
            f"Ignoring exception in wait_and_find_elements({by}, {value}): we tried, but sometimes empty results are normal: {repr(e)}"
        )
        pass

    return root.find_elements(by, value)


def wait_and_find_elements_cond(
    driver, by, value, cond_func, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None
):
    root = root_element if root_element else driver
    try:
        WebDriverWait(root, float(timeout)).until(lambda d: cond_func(d.find_elements(by, value)))
    except Exception as e:
        logger.info(
            f"Ignoring exception in wait_and_find_elements_cond({by}, {value}, {repr(cond_func)}): we tried, but sometimes empty results are normal: {repr(e)}"
        )
        pass

    res = root.find_elements(by, value)
    return res


def wait_and_find_elements_updated(
    driver, by, value, old_keys, key_extractor, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None
):
    return wait_and_find_elements_cond(
        driver,
        by,
        value,
        lambda elements: len(set(key_extractor(elements)).difference(old_keys)) > 0,
        timeout,
        root_element,
    )


def wait_and_find_element_and_click(driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None):
    node = wait_and_find_element_clickable(driver, by, value, timeout, root_element)
    ActionChains(driver).click(node).perform()


def wait_and_find_element_and_click_safe(
    driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None
):
    node = wait_and_find_element_clickable(driver, by, value, timeout, root_element)
    # Sometimes websites throttle the connection on clicking with ActionChain method and page times out.
    # This click is exclusive to undetected chromedriver and cannot be used with other browsers.
    node.click_safe()


def wait_and_find_element_and_hover(driver, by, value, timeout=DEFAULT_REQUIRED_LOADING_TIMEOUT, root_element=None):
    node = wait_and_find_element_visible(driver, by, value, timeout, root_element)
    ActionChains(driver).move_to_element(node).pause(0.1).perform()


def driver_decorator(C):
    # TODO obtain this list automatically be registring functions with an extra decorator
    methods = [
        "wait_and_find_element",
        "wait_and_find_element_visible",
        "wait_and_find_element_clickable",
        "wait_and_find_elements",
        "wait_and_find_elements_cond",
        "wait_and_find_elements_updated",
        "wait_and_find_element_and_click",
        "wait_and_find_element_and_click_safe",
        "wait_and_find_element_and_hover",
    ]
    for m in methods:
        setattr(C, m, eval(m))
    return C


@driver_decorator
class WrappedUndetectedChrome(uc.Chrome):
    # We change the default data path to avoid conflicts when running multiple instances of chrome
    Patcher.data_path = os.path.abspath(os.path.expanduser(f"~/.local/share/undetected_chromedriver/{os.getpid()}"))


@driver_decorator
class WrappedWebdriverChrome(webdriver.Chrome):
    pass
