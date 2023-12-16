import time
from selenium_driver import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
    TimeoutException,
    ElementNotVisibleException,
    MoveTargetOutOfBoundsException,
)
from selenium.webdriver.common.action_chains import ActionChains
from random import randint


def refresh_page(driver, config):
    """
    Refresh the current page. Sometimes required to load page correctly.
    Config_options:
        - before_pause_time (required): wait time before refresh
        - after_pause_time (optional): wait time before refresh
    """
    before_pause_time = config.before_pause_time
    after_pause_time = config.after_pause_time

    # Skip refresh if stop element found
    if stop_action_module(driver, config):
        return

    # Wait to load page
    time.sleep(float(before_pause_time))

    # Check for presence of stop element and ignore refresh if present
    if stop_action_module(driver, config):
        return

    # refresh page
    driver.refresh()

    # Wait after refresh
    time.sleep(float(after_pause_time))
    return


def click_shadow_root_element(driver, config):
    """
    Click element within a #shadow-root

    Config_options:
        - css_selector (required): Shadow Host CSS selector | DOM element containing #shadow-root element
        - clickable_css_selector (required): Shadow root element to click | Relative to Shadow Host
        - loading_delay (optional): wait time before/after click
    """
    shadow_host_css_selector = config.css_selector
    shadow_element_css_selector = config.clickable_css_selector
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    try:
        shadow_host = driver.wait_and_find_element(By.CSS_SELECTOR, shadow_host_css_selector, loading_timeout)
        shadow_root = shadow_host.shadow_root
        driver.wait_and_find_element_and_click(
            By.CSS_SELECTOR, shadow_element_css_selector, loading_timeout, root_element=shadow_root
        )

        time.sleep(float(loading_delay))
        return True

    except Exception as e:
        logger.info(f"Exception on click_shadow_root_element. Exception: {e}")
        return False


def scroll_to_load_element(driver, config):
    """
    Scroll to load element. Sometimes elements are loaded after scrolling the page a few times
    Config_options:
        - stop_css_selector (required): css selector of element to load by scrolling
        - scroll_pause_time (optional): wait time after scrolling
    """
    stop_css_selector = config.stop_css_selector
    scroll_pause_time = config.scroll_pause_time

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
            ActionChains(driver).send_keys(Keys.DOWN).perform()
            time.sleep(scroll_sleep)
            if time.time() > endtime:
                break
        try:
            WebDriverWait(driver, scroll_pause_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, stop_css_selector))
            )
            break
        except Exception:
            logger.info("Element not located. Scrolling some more")
            pass
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return window.pageYOffset")
        scroll_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height + driver.get_window_size()["height"] + scroll_tolerance_action > scroll_height:
            is_at_bottom = True
            logger.info("On scroll_to_load_element. Scrolled to bottom. Stop element not found")
            return

        nb_scroll += 1
    return


def relative_scroll(driver, config):
    """
    Scroll relative to an element. (Sometimes scroll only works after clicking inside an element in the page)
    Possible use case when scroll_down_after_get_new_page does not work.
    Config_options:
        - css_selector (required): relative element css selector
        - loading_delay (optional): wait time before scrolling
    """
    scroll_element_css_selector = config.css_selector
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    is_at_bottom = False
    time_scroll_action = 3
    scroll_tolerance_action = 100
    scroll_sleep = 0.1
    max_scroll = 20
    nb_scroll = 0

    try:
        WebDriverWait(driver, loading_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, scroll_element_css_selector))
        )
    except NoSuchElementException:
        logger.info(
            f"NoSuchElementException on action_before_search_pages_browsing_module.\nCSS_SELECTOR: {scroll_element_css_selector}"
        )
        return False

    element = driver.wait_and_find_element(By.CSS_SELECTOR, scroll_element_css_selector, loading_timeout)
    while not is_at_bottom and nb_scroll < max_scroll:
        # Scroll down 50px inside the element during 3s
        endtime = time.time() + time_scroll_action
        while True:
            driver.execute_script("arguments[0].scrollBy(0, 50)", element)
            time.sleep(scroll_sleep)
            if time.time() > endtime:
                break

        # Calculate new scroll height and compare with last scroll height of the element
        new_height = driver.execute_script(f"return document.querySelector('{scroll_element_css_selector}').scrollTop")
        scroll_height = driver.execute_script(
            f"return document.querySelector('{scroll_element_css_selector}').scrollHeight"
        )
        if new_height + driver.get_window_size()["height"] + scroll_tolerance_action > scroll_height:
            is_at_bottom = True

        nb_scroll += 1

    time.sleep(float(loading_delay))
    return


def switch_to_iframe(driver, config, css_selector=None):
    """
    Switch chromedriver focus to an iframe

    Config_options:
        - css_selector (required): iframe css selector
        - loading_delay (optional): wait time before selecting iframe
    """
    iframe_css_selector = config.css_selector if css_selector is None else css_selector
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    time.sleep(float(loading_delay))
    try:
        WebDriverWait(driver, float(loading_timeout)).until(
            EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, iframe_css_selector))
        )
        return True
    except Exception:
        logger.info("Exception on switching to iframe.")
        return False


def switch_out_iframe(driver, config):
    """
    Switch chromedriver focus to default content, if switched to iframe
    """
    try:
        driver.switch_to.default_content()
    except Exception as e:
        logger.info(f"Exception on switching to default content. Exception: {repr(e)}")
    return


def find_element_and_click(driver, config, css_selector=None, root_element=None):
    """
    This method is used to try and by pass the obstacles when trying to click on an element.
    This was implemented as not one option was always the correct way to intercept the clickable element

    Config options:
        - css_selector (required): css selector to retrieve clickable next page button
        - scroll_pause_time (optional): pause time after each scroll
        - loading_delay (optional): pause time after each action
        - elem_text_contains (optional): part of elem.text to locate it
    """

    css_selector = config.css_selector if css_selector is None else css_selector
    elem_text_contains = config.elem_text_contains
    scroll_pause_time = config.scroll_pause_time
    loading_timeout = config.loading_timeout
    undetected_click = config.undetected_click
    force_javascript_click = config.force_javascript_click

    # Method 0 javascript click for cases no other clicks work
    if force_javascript_click:
        try:
            element = driver.find_element(By.CSS_SELECTOR, css_selector)
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception as e:
            logger.info(f"Exception on click safe method 0 for selector {css_selector}: {repr(e)}")

    # Method 1 Cick safe method. This is exclusive to undetected chromedriver.
    if undetected_click:
        try:
            driver.wait_and_find_element_and_click_safe(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
            return True
        except Exception as e:
            logger.info(f"Exception on click safe method 1 for selector {css_selector}: {repr(e)}")

    if elem_text_contains:
        next_page_clickable_element = next(
            filter(
                lambda elem: elem_text_contains in elem.text,
                driver.wait_and_find_elements(
                    By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
                ),
            ),
            None,
        )
    else:
        # Method 2 Click by waiting for element to be clickable due to oerlays
        try:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
            return True
        except Exception as e:
            logger.info(f"Exception on find_element_and_click method 2 for selector {css_selector}: {repr(e)}")

        next_page_clickable_element = driver.wait_and_find_element(
            By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
        )

    # Scroll down to the next_page element
    # TODO replace JS scripts with selenium actions to avoid detection
    driver.execute_script("arguments[0].scrollIntoView(false);", next_page_clickable_element)

    # Wait to load page
    time.sleep(float(scroll_pause_time))

    # Method 3 Click by Action ActionChain
    try:
        # to avoid ElementClickInterceptedException if another element want receive click,
        # and button can be focused for clear click
        driver.execute_script("window.scrollTo(0, 0);")
        actions = ActionChains(driver)
        actions.move_to_element(next_page_clickable_element).perform()

        # click on next page
        next_page_clickable_element.click()
        return True
    except Exception as e:
        logger.info(f"Exception on find_element_and_click method 3 for selector {css_selector}: {repr(e)}")

    # Method 4 Click by scroll down (one screen height) from element while cant click
    try:
        actions = ActionChains(driver)
        actions.move_to_element(next_page_clickable_element).perform()
        default_page_y_offset = driver.execute_script("return window.pageYOffset")
        current_page_y_offset = default_page_y_offset
        window_height = driver.execute_script("return window.innerHeight")
        # to avoid endless loops
        max_scrolls = 5
        while current_page_y_offset <= default_page_y_offset + window_height and max_scrolls != 0:
            max_scrolls -= 1
            previous_page_y_offset = driver.execute_script("return window.pageYOffset")
            driver.execute_script(
                "window.scrollBy(0, arguments[0]);",
                next_page_clickable_element.size["height"],
            )
            current_page_y_offset = driver.execute_script("return window.pageYOffset")
            # If no space (windows height) for scroll
            if previous_page_y_offset == current_page_y_offset:
                break
            try:
                next_page_clickable_element.click()
                return True
            except Exception:
                pass
            time.sleep(float(scroll_pause_time))
        # Try the regular click method
        next_page_clickable_element.click()
        return True

    except MoveTargetOutOfBoundsException:
        # When all above methods return MoveTargetOutOfBoundsException. Using javascript is the only way to click elements sometimes.
        logger.info(
            "MoveTargetOutOfBoundsException on all methods when trying to click. Attempting to click with Javascript"
        )
        driver.execute_script("arguments[0].click(true);", next_page_clickable_element)
        return True
    except Exception as e:
        logger.info(f"Exception on find_element_and_click method 4 for selector {css_selector}: {repr(e)}")

    return False


def click_action_module_and_scroll(driver, config):
    """
    Click on one or multiple css selectors then scroll directly to bottom

    Config options:
        - css_selector (required): css selector to retrieve clickable next page button
        - scroll_pause_time (optional): pause time after each scroll
    """

    def click_action_fc(css_selector):
        scroll_pause_time = config.scroll_pause_time
        time.sleep(float(scroll_pause_time))

        try:
            find_element_and_click(driver, config, css_selector=css_selector)
        except (
            NoSuchElementException,
            ElementClickInterceptedException,
            ElementNotInteractableException,
            ElementNotVisibleException,
        ):
            pass
        except TimeoutException:
            pass

    css_selector = config.css_selector
    after_pause_time = config.after_pause_time

    if type(css_selector) is list:
        for css_sel in css_selector:
            click_action_fc(css_sel)
            time.sleep(float(after_pause_time))

    else:
        click_action_fc(css_selector)
        time.sleep(float(after_pause_time))

    return


def close_xdg_open_prompt(driver, config):
    """
    Close 'xdg-open' window

    before_pause_time (optional): pause time before navigation
    after_pause_time (optional): pause time after navigation
    """

    after_pause_time = config.after_pause_time
    before_pause_time = config.before_pause_time

    time.sleep(float(before_pause_time))
    try:
        driver.back()
        driver.forward()
        time.sleep(float(after_pause_time))
    except Exception as ex:
        logger.info(f"Exception on click_action_module {str(ex)}")

    return


def stop_action_module(driver, config):
    """
    Check presence of Stop element/value and ignore calling action module, if present.

    Config options:
        - stop_css_selector (optional): Do not execute action if this element is present
        - stop_value (optional): Check for presence of 'value' in stop_css_selector and exit if present. Will only check for stop element if stop_value is not defined
        - stop_attribute_name (optional): Stop element attribute to check for presence of 'value'. textContent by deafult
    """
    stop_css_selector = config.stop_css_selector
    loading_timeout = config.loading_timeout
    if stop_css_selector:
        stop_value = config.stop_value
        stop_attribute_name = config.stop_attribute_name if config.stop_attribute_name else "textContent"

        stop_element = driver.wait_and_find_elements(By.CSS_SELECTOR, stop_css_selector, loading_timeout)

        if stop_element:
            if not stop_value:
                logger.info("Stop element found. Ignoring action module")
                return True
            stop_attribute_content = stop_element[0].get_attribute(stop_attribute_name)
            if stop_attribute_content:
                if stop_value in stop_attribute_content.strip():
                    logger.info("Stop value found. Ignoring action module")
                    return True
    return False


def click_action_module(driver, config):
    """
    Click on one or multiple css selector

    Config options:
        - css_selector (required): css selector to retrieve clickable next page button
        - before_pause_time (optional): pause time before click
        - close_alert (optional): true if alert window appears on page to close it
    """
    close_alert = config.close_alert

    def click_action(css_selector):
        before_pause_time = config.before_pause_time
        after_pause_time = config.after_pause_time

        try:
            # Wait to load page
            time.sleep(float(before_pause_time))

            # click on next page
            find_element_and_click(driver, config, css_selector=css_selector)

            # Wait after click
            time.sleep(float(after_pause_time))
        except (
            NoSuchElementException,
            ElementClickInterceptedException,
            ElementNotInteractableException,
            ElementNotVisibleException,
        ):
            pass
        except TimeoutException:
            pass

    if stop_action_module(driver, config):
        return

    css_selector = config.css_selector

    if type(css_selector) is list:
        for css_sel in css_selector:
            click_action(css_sel)

    else:
        click_action(css_selector)

    if close_alert:
        try:
            driver.switch_to.alert.accept()
        except Exception as ex:
            logger.info(f"Exception on click_action_module {str(ex)}")
    return


def slider_bypass(driver, config):
    """
    Pass slider captcha

    Config options:
        - draggable_css_selector (required): movable part of slider css selector
        - restart_button_css_selector (required): clickable elem to restart captcha
        - attempts_count (optional): attempts to pass the captcha
        - slider_box_size (required): size of slider box in pixels
        - slider_bar_size (required): size of draggable slider bar in pixels
        - loading_delay (optional): waiting time before captcha loads and before restart_button loads
    """
    iframe_css_selector = config.iframe_css_selector
    draggable_css_selector = config.draggable_css_selector
    restart_button_css_selector = config.restart_button_css_selector
    attempts_count = config.attempts_count
    slider_box_size = config.slider_box_size
    slider_bar_size = config.slider_bar_size
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    switched_to_iframe = False

    if iframe_css_selector:
        switched_to_iframe = switch_to_iframe(driver, config, css_selector=iframe_css_selector)

    offset = slider_box_size - slider_bar_size

    for attempt in range(attempts_count):
        # distance = 0
        time.sleep(float(loading_delay))
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, draggable_css_selector)))
            time.sleep(float(loading_delay))
        except NoSuchElementException:
            logger.info("NoSuchElementException on slider_by_pass. No Slider Detected")
            break
        try:
            draggable_element = driver.wait_and_find_element(By.CSS_SELECTOR, draggable_css_selector, loading_timeout)
            random_offset = randint(0, 2)
            # random_offset=0
            ActionChains(driver).drag_and_drop_by_offset(
                draggable_element, offset + random_offset, 0
            ).release().perform()
        except MoveTargetOutOfBoundsException as ex:
            logger.info(f"MoveTargetOutOfBoundsException on slider_by_pass. Exception: {str(ex)}")
            pass
        except NoSuchElementException:
            break
        try:
            time.sleep(loading_delay)
            driver.wait_and_find_element_and_click(By.CSS_SELECTOR, restart_button_css_selector, loading_timeout)
        except (NoSuchElementException, ElementNotInteractableException):
            break
        logger.info(f"slider_bypass attempt {attempt+1}")

    if iframe_css_selector and switched_to_iframe:
        driver.switch_to.default_content()

    return
