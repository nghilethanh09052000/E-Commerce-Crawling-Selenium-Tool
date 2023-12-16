import json
import re
import time
from datetime import datetime
from selenium import webdriver
from jsonpath_ng import parse
from selenium_driver import logger
import sentry_sdk
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    MoveTargetOutOfBoundsException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium_driver.helpers.s3 import upload_image_from_bytes
from selenium_driver import actions as actions_modules
from app.helpers.utils import clean_url


def output_wrapper(func):
    def wrapper(*args, **kwargs):
        """
        This wrapper resolves the issues of binary \x00 NULL being passed with the string
        which is failing to be saved in the database
        """
        result = func(*args, **kwargs)
        try:
            if type(result) is str:
                result = result.replace("\x00", " ").replace("\xa0", " ")
                result = result.strip()
            return result
        except Exception as ex:
            logger.info(f"Exception on output_wrapper: {repr(ex)}")
            return result

    return wrapper


def resub_replace(replace_old, replace_new, input_string):
    return re.sub(
        bytes(replace_old, "utf-8"),
        bytes(replace_new, "utf-8"),
        bytes(input_string.strip(), "utf-8"),
    ).decode()


def _decode(string_value):
    try:
        return string_value.decode()
    except AttributeError:
        return string_value


@output_wrapper
def get_attribute_value(driver, config, root_element):
    css_selector = config.css_selector
    # Fallback selector if css selector times out
    css_selector_2 = config.css_selector_2
    attribute_name = "textContent" if not config.attribute_name else config.attribute_name
    regex = config.regex
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    replace_old = config.replace_old
    replace_new = config.replace_new
    exclude_children = config.exclude_children
    trim_text = config.trim_text
    input_format = config.input_format
    output_format = config.output_format
    clickable_css_selector = config.clickable_css_selector
    iframe_css_selector = config.iframe_css_selector
    escape_popup_on_end = config.escape_popup_on_end
    shadow_host_css_selector = config.shadow_host_css_selector

    # Button to close popup after click
    close_button_css_selector = config.close_button_css_selector

    # click before getting value
    if clickable_css_selector:
        try:
            actions_modules.find_element_and_click(driver, config, clickable_css_selector)
        except Exception:
            pass

    switched_to_iframe = False
    if iframe_css_selector:
        switched_to_iframe = actions_modules.switch_to_iframe(driver, config, css_selector=iframe_css_selector)

    try:
        if shadow_host_css_selector:
            shadow_host = driver.wait_and_find_element(By.CSS_SELECTOR, shadow_host_css_selector, loading_timeout)
            shadow_root = shadow_host.shadow_root
            elem = driver.wait_and_find_element(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=shadow_root
            )
        else:
            elem = driver.wait_and_find_element(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
    except TimeoutException:
        if css_selector_2:
            logger.info(
                f"TimeoutException on get_attribute_value at css_selector:{css_selector}. Trying with css_selector_2:{css_selector_2}."
            )
            try:
                elem = driver.wait_and_find_element(
                    By.CSS_SELECTOR, css_selector_2, loading_timeout, root_element=root_element
                )
            except TimeoutException:
                logger.info(f"TimeoutException on get_attribute_value at css_selector_2:{css_selector}")
                return
        else:
            logger.info(f"TimeoutException on get_attribute_value at css_selector:{css_selector}.")
            return

    try:
        text = elem.get_attribute(attribute_name)

        if exclude_children:
            children_text = [
                child.get_attribute("textContent")
                for child in driver.wait_and_find_elements(
                    By.CSS_SELECTOR, ":scope>*", loading_timeout, root_element=elem
                )
            ]
            for child_text in children_text:
                text = text.replace(child_text, "")

        if trim_text:
            text = "".join(text.strip().split())
        else:
            text = text.strip()

        if regex:
            text = re.findall(bytes(regex, "utf-8"), bytes(text, "utf-8"))
            if text != []:
                text = _decode(text[0])
            else:
                text = None

        if text is not None and replace_old is not None and replace_new is not None:
            text = resub_replace(replace_old, replace_new, text)

        if escape_popup_on_end:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()

        if switched_to_iframe:
            driver.switch_to.default_content()

    except Exception as e:
        logger.info(
            f"Exception on get_attribute_value. Driver url:{driver.current_url if driver.current_url else 'Element'}, Loading_delay:{loading_delay}, config: {config}, Exception:{repr(e)}"
        )
        if switched_to_iframe:
            driver.switch_to.default_content()
        return None

    # Try to close popup
    if close_button_css_selector:
        try:
            actions_modules.find_element_and_click(driver, config, close_button_css_selector)
        except TimeoutException:
            pass

    if input_format and output_format:
        text = datetime.strptime(text, input_format).strftime(output_format)

    return text


@output_wrapper
def get_attribute_url(driver, config, root_element):
    """
    used to clean up urls from query string
    """
    value = get_attribute_value(driver, config, root_element)
    if value is not None:
        return clean_url(value, config.post_url_cleaning_module)
    return value


@output_wrapper
def get_json_value(driver, config, root_element):
    """
    Usage:

    <head>
        <script type="application/ld+json">{"trash": {"some": "thing"}}</script>
        <script type="application/ld+json">{"foo": {"bar": "baz"}}</script>
    </head>

    css_selector: 'script[type="application/ld+json"]'
    output_string: '{jsons[1]["foo"]["bar"]} this is {jsons[0]["trash"]["some"]}'
    >>> baz this is thing

    Config options:
        - css_selector (required): css selector to retrieve elements that includes json
        - output_string (required): keys to obtain value from json
        - attribute_name (optional): element attribute name ('text' by default) where is json present as attribute value
        - loading_delay (optional): maximum time to wait for element loading
    """
    css_selector = config.css_selector
    output_string = config.output_string
    attribute_name = "text" if not config.attribute_name else config.attribute_name
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    replace_old = config.replace_old
    replace_new = config.replace_new

    try:
        driver.wait_and_find_element(By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element)
    except TimeoutException:
        logger.info(
            f"Timeout on get_json_value. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
        )
        return

    try:
        json_elems = driver.wait_and_find_elements(
            By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
        )
        jsons = []
        for elem in json_elems:
            jsons.append(json.loads(elem.get_attribute(attribute_name)))

        jsons_list_keys = re.findall("\{(jsons[^\}]+)\}", output_string)
        for key in jsons_list_keys:
            try:
                output_string = output_string.replace(f"{key}", str(eval(key))).replace("{", "").replace("}", "")
            except Exception:
                output_string = output_string.replace(f"{key}", "").replace("{", "").replace("}", "")
                logger.info(
                    f"key {key} not found in json on get_json_value, replaced to ''. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
                )

        if replace_old and replace_new:
            return resub_replace(replace_old, replace_new, output_string)
    except Exception as e:
        logger.info(
            f"{str(e)} on get_json_value. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        return

    return output_string


@output_wrapper
def get_multiple_text_content_and_concatenate(driver, config, root_element):
    """
    Config options:
        - css_selectors (required): css selectors to retrieve element
        - loading_delay (optional): maximum time to wait for element loading
        - replace_old (optional): string to replace in final expression (will preconvert to bytes)
        - replace_new (optional): string to replace by (will preconvert to bytes)
    """
    css_selectors = config.css_selectors
    has_multiple_items_in_same_selector = config.has_multiple_items_in_same_selector
    loading_timeout = config.loading_timeout
    replace_old = config.replace_old
    replace_new = config.replace_new

    text = ""

    for css_selector in css_selectors:
        # wait for the element to be fully loaded if necessary
        try:
            driver.wait_and_find_element(By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element)
            if has_multiple_items_in_same_selector:
                elems = driver.wait_and_find_elements(
                    By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
                )
                for elem in elems:
                    text += elem.get_attribute("textContent").strip()
                    text += "\n"
            else:
                elem = driver.wait_and_find_element(
                    By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
                )
                text += elem.get_attribute("textContent").strip()
                text += "\n"

        except TimeoutException:
            logger.info(
                f"Timeout on get_multiple_text_content_and_concatenate. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
            )
            pass
    if replace_old and replace_new:
        return resub_replace(replace_old, replace_new, text)
    else:
        return text


def get_subito_item(driver, config, root_element):
    item_css_selector = "#__NEXT_DATA__"
    loading_timeout = config.loading_timeout

    # wait for the element to be fully loaded if necessary
    try:
        driver.wait_and_find_element(By.CSS_SELECTOR, item_css_selector, loading_timeout, root_element=root_element)

    except TimeoutException:
        logger.info(
            f"Timeout on subito_date_retriever. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{None}"
        )
        return

    elem = driver.wait_and_find_element(By.CSS_SELECTOR, item_css_selector, loading_timeout, root_element=root_element)

    item = json.loads(elem.get_attribute("textContent"))["props"]["state"]["detail"]["item"]

    return item


def subito_date_retriever(driver, config, root_element):
    item = get_subito_item(driver, config, root_element)

    if item:
        return item["date"]

    return None


def subito_location_retriever(driver, config, root_element):
    item = get_subito_item(driver, config, root_element)

    if item:
        region = item["geo"]["region"]["value"]
        town = item["geo"]["town"]["value"]

        return f"{town} ({region})"

    return None


def get_pictures_from_attribute(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - loading_delay (optional): maximum time to wait for element loading
        - regex (optional): regex to search picture with
    """

    css_selector = config.css_selector
    attribute_name = config.attribute_name
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    remove_if_match_regex = config.remove_if_match_regex
    regex = config.regex

    time.sleep(float(loading_delay))

    pictures = []
    try:
        pictures = [
            ref.get_attribute(attribute_name)
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
            if ref.get_attribute(attribute_name)
        ]

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        pass

    if regex:
        pictures = [re.search(regex, picture).group(1) for picture in pictures if re.search(regex, picture)]
    if remove_if_match_regex:
        pictures_filtered = set([link for link in pictures if not re.search(remove_if_match_regex, link)])

        return list(set(pictures_filtered))

    return list(set(pictures))


def get_pictures_from_carousel_after_click(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - loading_delay (optional): maximum time to wait for element loading
    """
    clickable_css_selector = config.clickable_css_selector
    picture_css_selector = config.picture_css_selector
    attribute_name = config.attribute_name
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    pictures = []
    try:
        driver.wait_and_find_element_and_click(
            By.CSS_SELECTOR, clickable_css_selector, loading_timeout, root_element=root_element
        )
        time.sleep(float(loading_delay))
        pictures = [
            ref.get_attribute(attribute_name)
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, picture_css_selector, loading_timeout, root_element=root_element
            )
            if ref.get_attribute(attribute_name)
        ]

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_carousel_after_click. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        pass

    return list(set(pictures))


def get_pictures_from_attribute_with_replace(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - replace_old (required): string to replace in picture link
        - replace_new (required): string to replace by in picture link
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    replace_old = config.replace_old
    replace_new = config.replace_new
    replace_tail = config.replace_tail
    loading_timeout = config.loading_timeout

    pictures = []

    try:
        pictures = [
            ref.get_attribute(attribute_name).replace(replace_old, replace_new)
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
            if ref.get_attribute(attribute_name)
        ]
        if replace_tail:
            pictures = [picture.replace(replace_tail, "") for picture in pictures]

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute_with_replace. Driver url:{driver.current_url}, Config:{config}"
        )
        pass

    return list(set(pictures))


def get_pictures_from_attribute_with_replace_regex(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - replace_old_regex (required): regex pattern to replace in picture link
        - replace_new (required): string to replace by in picture link
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    replace_old_regex = config.replace_old_regex
    replace_new = config.replace_new
    loading_timeout = config.loading_timeout

    pictures = []

    try:
        if type(css_selector) is list:
            for selector in css_selector:
                pictures += [
                    re.sub(
                        replace_old_regex,
                        replace_new,
                        ref.get_attribute(attribute_name),
                    )
                    for ref in driver.wait_and_find_elements(
                        By.CSS_SELECTOR, selector, loading_timeout, root_element=root_element
                    )
                    if ref.get_attribute(attribute_name)
                ]
        else:
            pictures = [
                re.sub(replace_old_regex, replace_new, ref.get_attribute(attribute_name))
                for ref in driver.wait_and_find_elements(
                    By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
                )
                if ref.get_attribute(attribute_name)
            ]

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute_with_replace_regex. Driver url:{driver.current_url}, Config:{config}"
        )
        pass

    return list(set(pictures))


def get_pictures_between_2_attribute(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name_1 (required): attribute name to search in first
        - attribute_name_2 (required): attribute name to search in next
        - loading_delay (optional): maximum time to wait for element loading
    """
    css_selector = config.css_selector
    attribute_name_1 = config.attribute_name_1
    attribute_name_2 = config.attribute_name_2
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    time.sleep(float(loading_delay))

    pictures = []
    try:
        pictures = [
            ref.get_attribute(attribute_name_1)
            if ref.get_attribute(attribute_name_1)
            else ref.get_attribute(attribute_name_2)
            if ref.get_attribute(attribute_name_2)
            else None
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
        ]
        pictures = [p for p in pictures if p is not None]

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_between_2_attribute. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        pass

    return list(set(pictures))


def get_pictures_from_json(driver, config, root_element):
    """
    Picture function to get pictures from json

    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - json_attribute_name (required): json key where image list is located
        - json_index (optional): index of json element if more than one json for same css_selector
        - loading_delay (optional): wait time for element to load
        - replace_old (optional): regex pattern to substitute before parsing JSON string
        - replace_new (optional): string to replace regex pattern with
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    json_attribute_name = config.json_attribute_name
    loading_timeout = config.loading_timeout
    json_index = config.json_index
    replace_old = config.replace_old
    replace_new = config.replace_new

    try:
        driver.wait_and_find_element(By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element)
    except Exception:
        logger.info(
            f"Timeout on get_json_value. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
        )
        return

    json_elems = driver.wait_and_find_elements(
        By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
    )
    jsons = []
    for elem in json_elems:
        if replace_old and replace_new:
            json_string = resub_replace(replace_old, replace_new, elem.get_attribute(attribute_name))
        else:
            json_string = elem.get_attribute(attribute_name)
        jsons.append(json.loads(json_string))

    pictures = []
    entry = jsons[json_index]

    if type(entry) is list:
        for ent in entry:
            picture = [str(match.value) for match in parse(json_attribute_name).find(ent)]
            pictures.extend(picture)
    elif entry.get(json_attribute_name):
        pictures.extend(entry.get(json_attribute_name))

    logger.info(f"Pictures retrieved {pictures}")

    pictures = list(set(pictures))
    return pictures


def get_pictures_from_attribute_with_replace_and_split_suffix(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - replace_old (required): string to replace in picture link
        - replace_new (required): string to replace by in picture link
        - split_substring (required):
        - suffix_substring (required):
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    replace_old = config.replace_old
    replace_new = config.replace_new
    split_substring = config.split_substring
    suffix_substring = config.suffix_substring
    loading_timeout = config.loading_timeout

    pictures = []

    try:
        pictures = [
            ref.get_attribute(attribute_name).replace(replace_old, replace_new).split(split_substring)[0]
            + suffix_substring
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
            if ref.get_attribute(attribute_name)
        ]

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute_with_replace_and_split_suffix. Driver url:{driver.current_url}, Config:{config}"
        )
        pass

    return pictures


def get_pictures_from_attribute_with_one_picture_only_case(driver, config, root_element):
    """
    Config options:
        - css_selector_1 (required):
        - attribute_name_1 (required):
        - regex_1 (required):
        - replace_old_1 (required):
        - replace_new_1 (required):
        - css_selector_2 (required):
        - attribute_name_2 (required):
    """
    css_selector_1 = config.css_selector_1
    attribute_name_1 = config.attribute_name_1
    regex_1 = config.regex_1
    replace_old_1 = config.replace_old_1
    replace_new_1 = config.replace_new_1
    css_selector_2 = config.css_selector_2
    attribute_name_2 = config.attribute_name_2
    loading_timeout = config.loading_timeout

    pictures = []
    try:
        # Isolate strings of the format
        # background-image: url("https://apollo-singapore.akamaized.net:443/v1/files/wfkdznzii6rj3-ID/image;s=82x0");
        picture_containers = [
            ref.get_attribute(attribute_name_1)
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, css_selector_1, loading_timeout, root_element=root_element
            )
            if ref.get_attribute(attribute_name_1)
        ]

        # Retrieve the URL and resize the thumbnail image
        pictures = [
            re.search(regex_1, picture_container).group(1).replace(replace_old_1, replace_new_1)
            for picture_container in picture_containers
            if re.search(regex_1, picture_container)
        ]

        if not pictures:
            # Case when there is just one picture
            pic = driver.wait_and_find_element(
                By.CSS_SELECTOR, css_selector_2, loading_timeout, root_element=root_element
            ).get_attribute(attribute_name_2)
            if pic:
                pictures = [pic]
            else:
                pictures = []

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute_with_one_picture_only_case. Driver url:{driver.current_url}, Config:{config}"
        )
        pass

    return list(set(pictures))


def get_pictures_from_popup(driver, config, root_element):
    """
    Config options:
        - clickable_css_selector (optional): CSS selector to retrieve clickable element
        - picture_css_selector (required): CSS selector of all pictures
        - regex (required): regex to search picture with
        - attribute_name (required): attribute name to get to search for picture
        - escape_popup_on_end (optional): press escape to close popup
        - loading_delay (optional): time to wait after click
        - close_button_css_selector (optional): button to close popup
    """
    clickable_css_selector = config.clickable_css_selector
    picture_css_selector = config.picture_css_selector
    regex = config.regex
    attribute_name = config.attribute_name
    escape_popup_on_end = config.escape_popup_on_end
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    close_button_css_selector = config.close_button_css_selector
    pictures = []

    try:
        if clickable_css_selector:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, clickable_css_selector, loading_timeout, root_element=root_element
            )

        # Force updating the current page
        time.sleep(float(loading_delay))

        # Isolate strings of the format
        # background-image: url("https://cf.shopee.tw/file/2ba4fccee5c0bf5edc8e426d70a80ec4_tn");
        #  background-size: contain; background-repeat: no-repeat;
        picture_containers = driver.wait_and_find_elements(
            By.CSS_SELECTOR, picture_css_selector, loading_timeout, root_element=root_element
        )

        # Retrieve the URL and resize the thumbnail image
        pictures = [
            re.search(regex, picture_container.get_attribute(attribute_name)).group(1)
            for picture_container in picture_containers
            if re.search(regex, picture_container.get_attribute(attribute_name))
        ]

        if close_button_css_selector:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, close_button_css_selector, loading_timeout, root_element=root_element
            )

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_popup. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
        )
        pass

    if escape_popup_on_end:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    return pictures


def get_pictures_from_popup_with_multi_selectors(driver, config, root_element):
    """
    Config options:
        - clickable_css_selector (optional): Element to click before opening popup. Useful when video is focused by default
        - move_to_element_before_click (optional): Element to hover over before clicking clickable_css_selector_1
        - clickable_css_selector_1 (optional): CSS selector to retrieve clickable element
        - hover_before_click_css_selector (optional): css selector to hover over before clicking next picture. Use when click element not visible without hovering
        - clickable_css_selector_2 (required): CSS selector to click for get next picture
        - picture_css_selector (required): CSS selector of all pictures
        - replace_old (optional): string to replace in picture link
        - replace_new (optional): string to replace by in picture link
        - regex (required): regex to search picture with
        - attribute_name (required): attribute name to get to search for picture
        - loading_delay (optional): time to wait after click
        - loading_timeout (optional): time to wait until elements appear
        - escape_popup_on_end (optional): click on escape to close popup
        - close_button_css_selector (optional): button to close popup
        - skip_video (optional): Click next picture button if no element is found when True. This will happen only once.
    """
    clickable_css_selector = config.clickable_css_selector
    move_to_element_before_click = config.move_to_element_before_click
    clickable_css_selector_1 = config.clickable_css_selector_1
    hover_before_click_css_selector = config.hover_before_click_css_selector
    clickable_css_selector_2 = config.clickable_css_selector_2
    picture_css_selector = config.picture_css_selector
    replace_old = config.replace_old
    replace_new = config.replace_new
    regex = config.regex
    attribute_name = config.attribute_name
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    escape_popup_on_end = config.escape_popup_on_end
    close_button_css_selector = config.close_button_css_selector
    skip_video = config.skip_video
    pictures = set()

    try:
        if clickable_css_selector:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, clickable_css_selector, loading_timeout, root_element=root_element
            )
            time.sleep(float(loading_delay))
    except TimeoutException:
        logger.info(
            "Timeout on clickable_css_selector in get_pictures_from_popup_with_multi_selectors. Attempting to fetch pictures anyway."
        )
        pass
    try:
        if move_to_element_before_click:
            driver.wait_and_find_element_and_hover(By.CSS_SELECTOR, clickable_css_selector_1, loading_timeout)
            time.sleep(float(loading_delay))

        if clickable_css_selector_1:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, clickable_css_selector_1, loading_timeout, root_element=root_element
            )
            time.sleep(float(loading_delay))

        current_len = -1
        previous_pictures = set()  # pictures that we discovered on the previous iteration
        while len(pictures) != current_len:
            current_len = len(pictures)
            try:

                def extract_pictures(elements):
                    return set(
                        [
                            re.search(regex, e.get_attribute(attribute_name)).group(1)
                            for e in elements
                            if re.search(regex, e.get_attribute(attribute_name))
                        ]
                    )

                # Waiting for some progress compared to the previous iteration. Sometimes it takes a while between a click
                # on "clickable_css_selector_2" and actual update of "picture_css_selector".
                #
                # We're comparing new pictures with just the previous iteration and not with the total list of pictures so far.
                # This way, when we make a full circle to the first image it's seen as "progress" and no extra sleep happens.
                # Otherwise we would say "Oh, we've seen this picture before, no progress" and sleep needlessly.
                elements = driver.wait_and_find_elements_updated(
                    By.CSS_SELECTOR,
                    picture_css_selector,
                    previous_pictures,
                    extract_pictures,
                    timeout=loading_timeout,
                    root_element=root_element,
                )
                new_pictures = extract_pictures(elements)
                pictures.update(new_pictures)

                previous_pictures = new_pictures
                time.sleep(float(loading_delay))

            except Exception as e:
                logger.info(
                    f"Exception on picture_css_selector in get_pictures_from_popup_with_multi_selectors. Exception:{repr(e)}"
                )
                pass

            # Will try once again if skip_video and no element is found
            if len(pictures) == current_len and skip_video:
                skip_video = False
                current_len = -1

            try:
                if hover_before_click_css_selector:
                    driver.wait_and_find_element_and_hover(
                        By.CSS_SELECTOR, hover_before_click_css_selector, loading_timeout, root_element=root_element
                    )
                    time.sleep(loading_delay)

                driver.wait_and_find_element_and_click(
                    By.CSS_SELECTOR, clickable_css_selector_2, loading_timeout, root_element=root_element
                )
                time.sleep(loading_delay)
            except Exception as e:
                logger.info(
                    f"Exception on clickable_css_selector_2 in get_pictures_from_popup_with_multi_selectors. Exception:{repr(e)}"
                )
                break

        if escape_popup_on_end:
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()

        if close_button_css_selector:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, close_button_css_selector, loading_timeout, root_element=root_element
            )

    except TimeoutException as e:
        logger.info(
            f"TimeoutException on get_pictures_from_popup_with_multi_selectors. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Exception:{repr(e)}"
        )
        return
    except Exception as e:
        logger.info(f"Exception on get_pictures_from_popup_with_multi_selectors. Exception:{repr(e)}")
        return

    if replace_old is not None and replace_new is not None:
        pictures = [resub_replace(replace_old, replace_new, picture) for picture in pictures]

    return list(pictures)


def get_pictures_from_attribute_with_css_selector(driver, config, root_element):
    """
    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - loading_delay (optional): maximum time to wait for element loading
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    time.sleep(float(loading_delay))

    pictures = []
    try:
        for picture in driver.wait_and_find_elements(
            By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
        ):
            actions = ActionChains(driver)
            actions.move_to_element(picture).perform()
            time.sleep(float(loading_delay))
            if picture.get_attribute(attribute_name):
                pictures.append(picture.get_attribute(attribute_name))

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute_with_css_selector. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        return
    except Exception as e:
        logger.info(f"Exception on get_pictures_from_attribute_with_css_selector. Exception:{repr(e)}")
        return
    return list(set(pictures))


def get_pictures_by_clicking_thumbnails(driver, config, root_element):
    """
    Config options:
        - clickable_css_selector_1 (optional): Button to click before clicking thumbnails.(When thumbnails are within a carousel)
        - clickable_css_selector (required): Thumbnails to click for get next picture
        - picture_css_selector (required): CSS selector of all pictures
        - regex (required): regex to search picture with
        - attribute_name (required): attribute name to get to search for picture
        - loading_delay (optional): time to wait after click
        - loading_timeout (optional): time to wait until elements appear
        - escape_popup_on_end (optional): click on escape to close popup
    """

    clickable_css_selector_1 = config.clickable_css_selector_1
    clickable_css_selector = config.clickable_css_selector
    picture_css_selector = config.picture_css_selector
    regex = config.regex
    attribute_name = config.attribute_name
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    escape_popup_on_end = config.escape_popup_on_end
    pictures = []

    def get_pictures(css_selector):
        picture_containers = driver.wait_and_find_elements(
            By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
        )
        current_picture = [
            re.search(regex, picture_container.get_attribute(attribute_name)).group(1)
            for picture_container in picture_containers
            if re.search(regex, picture_container.get_attribute(attribute_name))
        ]
        return current_picture

    if clickable_css_selector_1:
        try:
            driver.wait_and_find_element_and_click(
                By.CSS_SELECTOR, clickable_css_selector_1, loading_timeout, root_element=root_element
            )
            time.sleep(float(loading_delay))
        except TimeoutException:
            logger.info(
                f"TimeoutException on clickable_css_selector_1 in get_pictures_by_clicking_thumbnails. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
            )
            return
    try:
        thumbnail_containers = driver.wait_and_find_elements(
            By.CSS_SELECTOR, clickable_css_selector, loading_timeout, root_element=root_element
        )
    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_by_clicking_thumbnails. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
        )
        return

    # Click each thumbnail and get full image
    for thumbnail_container in thumbnail_containers:
        try:
            ActionChains(driver).move_to_element(thumbnail_container).pause(0.1).click().perform()
            time.sleep(float(loading_delay))

        except MoveTargetOutOfBoundsException:
            # This shouldn't be required but, this is the only method which works, when move_to_element fails with MoveTargetOutOfBoundsException for some strange reason (example: miravia.es).
            logger.info("MoveTargetOutOfBoundsException on clicking thubnail. Trying to click with JavaScript")
            driver.execute_script("arguments[0].scrollIntoView();", thumbnail_container)
            time.sleep(0.1)
            driver.execute_script("arguments[0].click();", thumbnail_container)
            time.sleep(float(loading_delay))
        except Exception as e:
            logger.info(f"Exception when clicking thumbnail on get_pictures_by_clicking_thumbnails. Message:{repr(e)}")
            pass
        try:
            pictures += get_pictures(picture_css_selector)
        except Exception:
            logger.info(
                f"Exception on get_pictures_by_clicking_thumbnails. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
            )
            pass

        if escape_popup_on_end and not clickable_css_selector_1:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    # Try to get pcitures if no thumbnails are found. Useful for single picture cases
    if not thumbnail_containers:
        pictures = get_pictures(picture_css_selector)

    if escape_popup_on_end and clickable_css_selector_1:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    return list(set(pictures))


def get_pictures_from_attribute_with_replace_and_upload_to_s3(driver, config, root_element):
    """
    Custom vestairecollective picture function to bypass CloudFare protection

    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - replace_old (required): string to replace in picture link
        - replace_new (required): string to replace by in picture link
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    replace_old = config.replace_old
    replace_new = config.replace_new
    replace_tail = config.replace_tail
    loading_timeout = config.loading_timeout

    def get_pictures(attribute_name, replace_old, replace_new, replace_tail, css_selector):
        return [
            ref.get_attribute(attribute_name).replace(replace_old, replace_new).replace(replace_tail, "")
            for ref in driver.wait_and_find_elements(
                By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
            )
            if ref.get_attribute(attribute_name)
        ]

    pictures = []
    try:
        pictures = get_pictures(attribute_name, replace_old, replace_new, replace_tail, css_selector)
        logger.info(f"Pictures retrieved {pictures}")
    except TimeoutException:
        logger.info(
            f"TimeoutException on get_pictures_from_attribute_with_replace_and_upload_to_s3. Driver url:{driver.current_url}, Config:{config}"
        )
    except StaleElementReferenceException:
        for _ in range(0, 10):
            try:
                pictures = get_pictures(attribute_name, replace_old, replace_new, replace_tail, css_selector)
                logger.info(f"Pictures retrieved {pictures}")
                break
            except Exception:
                time.sleep(1)
    pictures = list(set(pictures))

    s3_pictures = []

    main_tab = driver.current_window_handle
    driver.switch_to.new_window("tab")

    for picture in pictures:
        try:
            logger.info(f"driver loading image {picture}, Config:{config}")

            driver.get(picture)
            img = driver.wait_and_find_element(By.CSS_SELECTOR, "img", loading_timeout).screenshot_as_png

            s3_picture_url, is_blacklisted_image = upload_image_from_bytes(img=img)
            logger.info(f"s3_picture_url : {s3_picture_url} - is_blacklisted_image:{is_blacklisted_image}")

            if s3_picture_url and not is_blacklisted_image:
                s3_pictures.append(s3_picture_url)

        except TimeoutException:
            logger.info(f"TimeoutException on getting image. Driver url:{driver.current_url}, Config:{config}")
            continue
        except Exception as e:
            logger.info(f"Exception on getting image {str(e)}. Driver url:{driver.current_url}, Config:{config}")
            sentry_sdk.capture_exception(e)

    # go back to post tab
    driver.close()
    driver.switch_to.window(main_tab)

    return s3_pictures


def get_pictures_from_json_and_upload_to_s3(driver, config, root_element):
    """
    Custom vestairecollective picture function to bypass CloudFare protection

    Config options:
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where is picture link
        - replace_old (optional): string to replace in picture link
        - replace_new (optional): string to replace by in picture link
    """
    css_selector = config.css_selector
    attribute_name = config.attribute_name
    json_attribute_name = config.json_attribute_name
    replace_old = config.replace_old
    replace_new = config.replace_new
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    try:
        driver.wait_and_find_element(By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element)
    except Exception:
        logger.info(
            f"Timeout on get_json_value. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        return

    json_elems = driver.wait_and_find_elements(
        By.CSS_SELECTOR, css_selector, loading_timeout, root_element=root_element
    )
    jsons = []
    for elem in json_elems:
        jsons.append(json.loads(elem.get_attribute(attribute_name)))

    pictures = []
    for entry in jsons:
        if entry.get(json_attribute_name):
            pictures.extend(
                entry.get(json_attribute_name)
                if type(entry.get(json_attribute_name)) == list
                else [entry.get(json_attribute_name)]
            )

    logger.info(f"Pictures retrieved {pictures}")

    pictures = list(set(pictures))

    original_url = driver.current_url

    s3_pictures = []
    for picture in pictures:
        try:
            if replace_old and replace_new is not None:
                picture = picture.replace(replace_old, replace_new)
            if picture.startswith("http://") or picture.startswith("https://"):
                logger.info(f"driver loading image {picture}, Config:{config}")

                driver.get(picture)
                img = driver.wait_and_find_element(
                    By.CSS_SELECTOR, "img", loading_timeout, root_element=root_element
                ).screenshot_as_png

                s3_picture_url, is_blacklisted_image = upload_image_from_bytes(img=img)

                logger.info(f"s3_picture_url : {s3_picture_url} - is_blacklisted_image:{is_blacklisted_image}")
                if s3_picture_url and not is_blacklisted_image:
                    s3_pictures.append(s3_picture_url)

        except TimeoutException:
            logger.info(f"TimeoutException on getting image. Driver url:{driver.current_url}, Config:{config}")
            continue
        except Exception as e:
            logger.info(f"Exception on getting image {str(e)}. Driver url:{driver.current_url}, Config:{config}")
            sentry_sdk.capture_exception(e)

    # go back to original url
    driver.get(original_url)
    logger.info(f"Final Pictures converted {s3_pictures}")
    return s3_pictures


def get_pictures_from_variants(driver, config, root_element):
    """
    Config options:
        - variants_css_selector (required): css selector to select variants
        - picture_module_name (required): Picture module to call after clicking each variant
        - after_puse_time (optional): Wait time after clicking on variant
    """

    variants_css_selector = config.variants_css_selector
    picture_module_name = config.picture_module_name
    loading_timeout = config.loading_timeout
    after_pause_time = config.after_pause_time
    picture_container = []

    # Store original URL
    original_url = clean_url(driver.current_url, config.post_url_cleaning_module)

    # Picture module to use after selecting variant
    picture_module = globals()[picture_module_name]

    variants_container = driver.wait_and_find_elements(
        By.CSS_SELECTOR, variants_css_selector, loading_timeout, root_element=root_element
    )

    for variant in range(len(variants_container)):
        ActionChains(driver).move_to_element(variants_container[variant]).pause(0.1).click().perform()
        time.sleep(float(after_pause_time))

        # Reinitialize variants objects to avoid StaleElementReference
        variants_container = driver.wait_and_find_elements(
            By.CSS_SELECTOR, variants_css_selector, loading_timeout, root_element=root_element
        )
        # Skip if URL changes after clicking on variant
        if clean_url(driver.current_url, config.post_url_cleaning_module) != original_url:
            continue

        # Call picture method for current variant
        picture_container += picture_module(driver, config, root_element)

    # Get pictures from current page, if variants not available
    if not variants_container:
        picture_container += picture_module(driver, config, root_element)

    return list(set(picture_container))


def click_then_get_attribute(driver, config, root_element):
    """
    Custom vestairecollective vendor function to get vendor id

    Config options:
        - button_css_selector (required): css selector to click before fetching element
        - css_selector (required): css selector to retrieve element
        - attribute_name (required): attribute name where text or link exists
        - click_opens_new_tab (optional): Set to true if clicking 'button_css_selector' opens a new tab. Default is False
        - replace_old (required): string to replace in attribute content
        - replace_new (required): string to replace by in attribute content
    """
    button_css_selector = config.button_css_selector
    click_opens_new_tab = config.click_opens_new_tab
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    original_url = driver.current_url

    try:
        driver.wait_and_find_element_and_click(
            By.CSS_SELECTOR, button_css_selector, loading_timeout, root_element=root_element
        )
        time.sleep(float(loading_delay))
    except TimeoutException:
        logger.info(
            f"Timeout on click_then_get_attribute. Driver url:{driver.current_url}, Loading_timeout:{loading_timeout}, Config:{config}"
        )
        return

    if click_opens_new_tab:
        # switch focus to new tab
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(float(loading_delay))

    elem = get_attribute_value(driver, config, root_element)

    if click_opens_new_tab:
        # close new tab and switch focus to parent tab
        driver.close()
        time.sleep(float(loading_delay))
        driver.switch_to.window(driver.window_handles[0])
    else:
        # go back to original url
        driver.get(original_url)
        time.sleep(float(loading_delay))

    return elem


def get_key_value_list(driver, config, root_element):
    """
    Config options:
        - clickable_css_selector (optional): one or more css selector to click before retrieve data
        - clickable_css_is_always_present (optional): false if it possible to get some data without click if element not in page
        - key_css_selector_attribute_name (optional): attribute name to get attribute value in elem
        - value_css_selector_attribute_name (optional): attribute name to get attribute value in elem
        - key_regex (optional): regex to extract a piece of text from an key element
        - value_regex (optional): regex to extract a piece of text from an value element
        - key_replace_old (optional): string to replace in final expression (will preconvert to bytes)
        - key_replace_new (optional): string to replace by (will preconvert to bytes)
        - value_replace_old (optional): string to replace in final expression (will preconvert to bytes)
        - value_replace_new (optional): string to replace by (will preconvert to bytes)
        - loading_delay (optional): time to wait after click
    """
    if type(config.clickable_css_selector) is list:
        clickable_css_selectors = config.clickable_css_selector
    elif type(config.clickable_css_selector) is str:
        clickable_css_selectors = [config.clickable_css_selector]
    else:
        clickable_css_selectors = None
    clickable_css_is_always_present = (
        True if config.clickable_css_is_always_present is None else config.clickable_css_is_always_present
    )
    key_css_selector = config.key_css_selector
    value_css_selector = config.value_css_selector
    key_regex = config.key_regex
    value_regex = config.value_regex
    key_css_selector_attribute_name = (
        "textContent" if not config.key_css_selector_attribute_name else config.key_css_selector_attribute_name
    )

    value_css_selector_attribute_name = (
        "textContent" if not config.value_css_selector_attribute_name else config.value_css_selector_attribute_name
    )

    key_replace_old = "[ ]+" if not config.key_replace_old else config.key_replace_old
    key_replace_new = " " if config.key_replace_new is None else config.key_replace_new
    value_replace_old = "[ ]+" if not config.value_replace_old else config.value_replace_old
    value_replace_new = " " if config.value_replace_new is None else config.value_replace_new
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout
    try:
        if clickable_css_selectors:
            try:
                time.sleep(float(loading_delay))
                for clickable_css_selector in clickable_css_selectors:
                    actions_modules.find_element_and_click(driver, config, clickable_css_selector)
                    time.sleep(float(loading_delay))
            except TimeoutException:
                if clickable_css_is_always_present:
                    logger.info(
                        f"TimeoutException on get_key_value_list. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
                    )
                    return
                else:
                    pass
        try:
            driver.wait_and_find_element(By.CSS_SELECTOR, key_css_selector, loading_timeout, root_element=root_element)
            driver.wait_and_find_element(
                By.CSS_SELECTOR, value_css_selector, loading_timeout, root_element=root_element
            )
        except TimeoutException:
            logger.info(
                f"Timeout on get_key_value_list. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
            )
            return

        # in first checking regex match (if it present in config) then send result in resub_replace func
        keys = []
        for elem in driver.wait_and_find_elements(
            By.CSS_SELECTOR, key_css_selector, loading_timeout, root_element=root_element
        ):
            key = elem.get_attribute(key_css_selector_attribute_name)

            if key_regex:
                key = re.findall(bytes(key_regex, "utf-8"), bytes(key.replace("\n", " "), "utf-8"))
                if key != []:
                    key = key[0].decode().strip()
                else:
                    key = None
            if key is not None:
                keys.append(resub_replace(key_replace_old, key_replace_new, key))

        values = []
        for elem in driver.wait_and_find_elements(
            By.CSS_SELECTOR, value_css_selector, loading_timeout, root_element=root_element
        ):
            value = elem.get_attribute(value_css_selector_attribute_name)
            if value_regex:
                value = re.findall(
                    bytes(value_regex, "utf-8"),
                    bytes(value.replace("\n", " "), "utf-8"),
                )
                if value != []:
                    value = value[0].decode().strip()
                else:
                    value = None
            if value is not None:
                values.append(resub_replace(value_replace_old, value_replace_new, value))
        if keys == [] and values == []:
            return
        else:
            key_value_dict = dict(zip(keys, values))
            if key_value_dict.get("", None) is not None:
                del key_value_dict[""]
            return key_value_dict

    except TimeoutException:
        logger.info(
            f"TimeoutException on get_key_value_list. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        pass
    except IndexError:
        logger.info(
            f"IndexError on get_key_value_list. Driver url:{driver.current_url}, Loading_delay:{loading_delay}, Config:{config}"
        )
        pass


def get_key_value_list_from_different_elements(driver, config, root_element):
    """
    Config options:
        - clickable_css_selectors (optional | strictly a list): list css selectors to click before retrieve
        - key_css_selectors (required): list of css selectors for "key" elements
        - value_css_selectors (required): list of css selectors for "value" elements
        - key_attributes (optional): list of attributes for "key" elements, "textContent" for all elems by default
        - value_attributes (optional): list of attributes for "value" elements, "textContent" for all elems by default
        - key_regex (optional): list of regex for "key" elements, "(.+)" for all elems by default
        - value_regex (optional): list of regex for "value" elements, "(.+)" for all elems by default
    """
    clickable_css_selectors = config.clickable_css_selectors
    key_css_selectors = config.key_css_selectors
    value_css_selectors = config.value_css_selectors
    key_attributes = config.key_attributes
    value_attributes = config.value_attributes
    key_regex = config.key_regex
    value_regex = config.value_regex
    loading_delay = config.loading_delay
    loading_timeout = config.loading_timeout

    @output_wrapper
    def get_wrapped(str_to_wrap):
        return str_to_wrap

    def get_key_or_value_list(elem_css_selectors, elem_attributes, elem_regex):
        out = []
        if not elem_regex:
            elem_regex = ["(.+)" for x in range(len(elem_css_selectors))]
        if not elem_attributes:
            elem_attributes = ["textContent" for x in range(len(elem_css_selectors))]
        for elem_css_selector in elem_css_selectors:
            index_in_list = elem_css_selectors.index(elem_css_selector)
            try:
                elem = driver.wait_and_find_element(
                    By.CSS_SELECTOR, elem_css_selector, loading_timeout, root_element=root_element
                )
                elem_attribute_value = elem.get_attribute(elem_attributes[index_in_list]).replace("\n", "")
                regex_out = re.findall(
                    bytes(elem_regex[index_in_list], "utf-8"),
                    bytes(elem_attribute_value, "utf-8"),
                )
                if regex_out != []:
                    out.append(get_wrapped(regex_out[0].decode()).strip())
                else:
                    out.append("")
            except (TimeoutException, AttributeError):
                out.append("")
        return out

    out_dict = {}

    if clickable_css_selectors:
        for clickable_css_selector in clickable_css_selectors:
            if clickable_css_selector != "":
                try:
                    time.sleep(float(loading_delay))
                    actions_modules.find_element_and_click(driver, config, clickable_css_selector)
                except TimeoutException:
                    pass

            out_dict.update(
                dict(
                    zip(
                        get_key_or_value_list(key_css_selectors, key_attributes, key_regex),
                        get_key_or_value_list(value_css_selectors, value_attributes, value_regex),
                    )
                )
            )
    else:
        out_dict.update(
            dict(
                zip(
                    get_key_or_value_list(key_css_selectors, key_attributes, key_regex),
                    get_key_or_value_list(value_css_selectors, value_attributes, value_regex),
                )
            )
        )
    if "" in out_dict:
        del out_dict[""]

    return out_dict
