import datetime
import os
import textwrap
import time
import traceback
from datetime import timezone
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from selenium_driver import logger
from selenium_driver.driver_wrapper import wait_and_find_element_and_click
from selenium_driver.helpers.s3 import upload_file_to_s3
from selenium_driver.settings import (
    ARCHIVING_DEFAULT_SCROLL_SLEEP,
    ARCHIVING_DEFAULT_SLEEP_AFTER_GET,
    ARCHIVING_DEFAULT_SLEEP_AFTER_OPERATIONS,
    ARCHIVING_DEFAULT_SLEEP_AFTER_SET_WINDOW_TO_REQUIRED_SIZE,
    ARCHIVING_MAX_SCROLL_ACTION,
    ARCHIVING_SCROLL_TOLERANCE_THRESHOLD,
    ARCHIVING_SLEEP_AFTER_CLICK_ACTION,
    ARCHIVING_SLEEP_AFTER_SCROLL_DOWN,
    ARCHIVING_SLEEP_AFTER_SCROLL_UP,
    ARCHIVING_TIME_SCROLL_ACTION,
    ENVIRONMENT_NAME,
    SPECIFIC_SCRAPER_AWS_BUCKET,
    sentry_sdk,
)

# STAMP CONSTANTS
FONT_SIZE = 20
FONT_COLOR = (255, 255, 255)
BACKGROUND_COLOR = (0, 0, 0, 120)
SHADOW_COLOR = (0, 0, 0)
TITLE_TEXT = "Screenshot"
BOX_MARGIN_X = 10
BOX_MARGIN_Y = 10
MAX_CHAR_ONE_LINE = 50
INTERLINE = 3

font = ImageFont.truetype("selenium_driver/archiving/fonts/Gibson-Book.ttf", FONT_SIZE)


def archive_post(driver, current_post, element_to_schoot=None):
    """Using the Chrome driver provided, make a screenshot of the current post

    Parameters
    ==========
    driver: Selenium Chrome webdriver
        driver in use for the scraping
    current_post: SQLAlchemy Post object
        post object that is being scraped
    element_to_shoot (optional):
        Used if we want to scrape an element of the page and not the whole page
        (the post of interest is one of many in the page)
    """

    try:
        archive_link = take_webshot(driver=driver, element_to_shoot=element_to_schoot, add_date_url_stamp=True)

        # store archive_url
        if archive_link:
            current_post.archive_link = archive_link
        else:
            logger.warn(f"Archiving failed for post {current_post.id}")

    except Exception as e:
        sentry_sdk.capture_exception(e)


def draw_outline_text(draw, x, y, text):
    # thin border
    draw.text((x - 1, y), text, font=font, fill=SHADOW_COLOR)
    draw.text((x + 1, y), text, font=font, fill=SHADOW_COLOR)
    draw.text((x, y - 1), text, font=font, fill=SHADOW_COLOR)
    draw.text((x, y + 1), text, font=font, fill=SHADOW_COLOR)

    # thicker border
    draw.text((x - 1, y - 1), text, font=font, fill=SHADOW_COLOR)
    draw.text((x + 1, y - 1), text, font=font, fill=SHADOW_COLOR)
    draw.text((x - 1, y + 1), text, font=font, fill=SHADOW_COLOR)
    draw.text((x + 1, y + 1), text, font=font, fill=SHADOW_COLOR)

    # now draw the text over it
    draw.text((x, y), text, font=font, fill=FONT_COLOR)


def add_date_url_stamp_to_image(file_path, url):
    # Text definition
    datetime_text = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    url_text = url
    url_lines = textwrap.wrap(url_text, width=MAX_CHAR_ONE_LINE)

    # Position definition
    title_text_width, title_text_height = font.getsize(TITLE_TEXT)
    datetime_text_width, datetime_text_height = font.getsize(datetime_text)
    url_text_width, url_text_height = (
        max([font.getsize(url_line)[0] for url_line in url_lines]),
        max([font.getsize(url_line)[1] for url_line in url_lines]),
    )
    url_text_height = url_text_height * len(url_lines) + (INTERLINE * len(url_lines) - 1)

    box_width = max(title_text_width, datetime_text_width, url_text_width) + 2 * BOX_MARGIN_X
    box_height = title_text_height + datetime_text_height + url_text_height + 4 * BOX_MARGIN_Y

    # Edit image by adding text
    box_image = Image.new("RGBA", (box_width, box_height), BACKGROUND_COLOR)

    box_draw = ImageDraw.Draw(box_image)
    box_draw.text(
        ((box_width - title_text_width) / 2, BOX_MARGIN_Y),
        TITLE_TEXT,
        FONT_COLOR,
        font=font,
    )
    box_draw.text(
        (BOX_MARGIN_X, BOX_MARGIN_Y + title_text_height + BOX_MARGIN_Y),
        datetime_text,
        FONT_COLOR,
        font=font,
    )
    for i, url_line in enumerate(url_lines):
        box_draw.text(
            (
                BOX_MARGIN_X,
                BOX_MARGIN_Y + title_text_height + (i + 1) * datetime_text_height + i * INTERLINE + 2 * BOX_MARGIN_Y,
            ),
            url_line,
            FONT_COLOR,
            font=font,
        )

    # put box on source image and save
    image = Image.open(file_path)
    width, height = image.size
    box_x, box_y = width - box_width - BOX_MARGIN_X, height - box_height - BOX_MARGIN_Y
    image.paste(box_image, (box_x, box_y), box_image)

    image.save(file_path)


def remove_elements(driver, css_selectors):
    for css_selector in css_selectors:
        try:
            # check element if it exists before trying to remove it to avoid js errors
            driver.execute_script(
                f"if (document.querySelector('{css_selector}')){{ document.querySelector('{css_selector}').remove();}}"
            )
        except Exception as e:
            print(e)
            pass


def click_on_elements(driver, css_selectors):
    for css_selector in css_selectors:
        try:
            wait_and_find_element_and_click(
                driver, By.CSS_SELECTOR, css_selector, timeout=ARCHIVING_SLEEP_AFTER_CLICK_ACTION
            )
            time.sleep(float(ARCHIVING_SLEEP_AFTER_CLICK_ACTION))
        except Exception as e:
            logger.error(f"click failed {repr(e)}")


def scroll_to_bottom(driver, scroll_sleep):
    is_at_bottom = False
    max_scroll = ARCHIVING_MAX_SCROLL_ACTION
    nb_scroll = 0
    while not is_at_bottom and nb_scroll < max_scroll:
        # Scroll down using down key during 3s
        endtime = time.time() + ARCHIVING_TIME_SCROLL_ACTION
        while True:
            webdriver.ActionChains(driver).send_keys(Keys.DOWN).perform()
            time.sleep(float(scroll_sleep))
            if time.time() > endtime:
                break

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return window.pageYOffset")
        scroll_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height + driver.get_window_size()["height"] + ARCHIVING_SCROLL_TOLERANCE_THRESHOLD > scroll_height:
            is_at_bottom = True

        nb_scroll += 1

    # Go back to top of the page
    time.sleep(float(ARCHIVING_SLEEP_AFTER_SCROLL_DOWN))
    driver.wait_and_find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + Keys.HOME)
    time.sleep(float(ARCHIVING_SLEEP_AFTER_SCROLL_UP))


def take_webshot(
    selenium_driver=None,
    url=None,
    element_to_shoot=None,
    css_selector_to_shoot=None,
    add_date_url_stamp=True,
    display_url=None,
    kill_driver=False,
):
    """Takes a screenshot of the given URL and returns the S3 storage URL of the image

    Parameters
    ==========
    driver: Selenium Webdriver
        if not provided, we create one
    url: str
        URL of the page to screenshot. If not provided, we use the current page of the driver
    element_to_shoot: Selenium Webelement
        Web element we want to screenshot
    css_selector_to_shoot: str
        CSS selector of the element we want to shoot
    add_date_url_stamp: bool
        whether to add a stamp in the URL which specifies the time and URL of the screenshot
    display_url: str
        if not provided, we put the current URL in the stamp. If provided, the current URL is overriden with display_url
    """

    if selenium_driver.driver is None and not url:
        raise AttributeError("Either driver or url must be defined when calling take_webshot()")

    # Get the URL of the page. If it is not provided as an argument, we use the current page of the driver
    page_url = url if url else selenium_driver.driver.current_url

    # Get the URL to add in the stamp (it will be added only if add_date_url_stamp is true)
    display_url = display_url if display_url else page_url

    # Add a random uuid to the file name
    file_path = f"{uuid4()}_webshot.png"
    s3_link = None

    # identify whether driver is only intialized for this task and should be killed at the end
    if selenium_driver.driver is None:
        # Initialize a driver
        selenium_driver.launch_driver()
        kill_driver = True

    # Make the screenshot
    try:
        archiving_options = selenium_driver.config.archiving_options
        logger.info(f"archiving_options {archiving_options}")
        if url:
            try:
                selenium_driver.get(url)
            except TimeoutException:
                pass

        sleep_after_get = archiving_options.sleep_after_get if archiving_options else ARCHIVING_DEFAULT_SLEEP_AFTER_GET
        time.sleep(float(sleep_after_get))

        elements_to_remove = archiving_options.remove_elements if archiving_options else []
        if len(elements_to_remove) > 0:
            logger.info(f"elements_to_remove {elements_to_remove}")
            remove_elements(driver=selenium_driver.driver, css_selectors=elements_to_remove)

        elements_to_click_on = archiving_options.click_on_elements if archiving_options else []
        if len(elements_to_click_on) > 0:
            logger.info(f"elements_to_click_on {elements_to_click_on}")
            click_on_elements(driver=selenium_driver.driver, css_selectors=elements_to_click_on)

        is_scroll_to_bottom = archiving_options.scroll_to_bottom if archiving_options else False
        if is_scroll_to_bottom:
            logger.info(f"is_scroll_to_bottom {is_scroll_to_bottom}")
            scroll_sleep = archiving_options.scroll_sleep if archiving_options else ARCHIVING_DEFAULT_SCROLL_SLEEP
            scroll_to_bottom(driver=selenium_driver.driver, scroll_sleep=scroll_sleep)

        sleep_after_operations = (
            archiving_options.sleep_after_operations if archiving_options else ARCHIVING_DEFAULT_SLEEP_AFTER_OPERATIONS
        )
        time.sleep(float(sleep_after_operations))

        if element_to_shoot or css_selector_to_shoot:
            save_element_screenshot(
                selenium_driver.driver,
                file_path,
                element=element_to_shoot,
                css_selector=css_selector_to_shoot,
            )
        else:
            # Make a screenshot of the whole page

            selenium_driver.driver.set_window_position(0, 0)

            # Save current dimensions of the window and restore to this size after screenshot
            current_width = selenium_driver.driver.get_window_size()["width"]
            current_height = selenium_driver.driver.get_window_size()["height"]

            # 2023-05-22: commented-out by salmin
            # different screen size breaks the scraping in some cases (e.g. wildberries.ru)
            # TODO: figure out what to do. Maybe keep the screen size intact in intermediate screenshots while scraping, but
            # then as the last one action with the page we can afford resizing it, right before the final screenshot.
            #
            # logger.info(f"height {height} - width {width}")
            # selenium_driver.driver.set_window_size(width, height)

            # # If both the height and the width are provided in the options, we don't use document.body.parentNode.scroll
            if not archiving_options or (not archiving_options.width and not archiving_options.height):
                # screenshots seem to have a limit height of 16310px
                required_width = min(
                    selenium_driver.driver.execute_script("return document.body.parentNode.scrollWidth"),
                    2000,
                )
                required_height = min(
                    selenium_driver.driver.execute_script("return document.body.parentNode.scrollHeight"),
                    3000,
                )

                selenium_driver.driver.set_window_size(required_width, required_height)

            time.sleep(float(ARCHIVING_DEFAULT_SLEEP_AFTER_SET_WINDOW_TO_REQUIRED_SIZE))

            selenium_driver.driver.save_screenshot(file_path)

            # Restore window to initial size
            selenium_driver.driver.set_window_size(current_width, current_height)

        if add_date_url_stamp:
            add_date_url_stamp_to_image(file_path, display_url)

        _, s3_link = upload_file_to_s3(
            local_file=file_path,
            bucket=SPECIFIC_SCRAPER_AWS_BUCKET,
            file_name=f"{ENVIRONMENT_NAME}/webshots/{uuid4()}.png",
            file_type="image/png",
        )

    except Exception as e:
        print(e)
        sentry_sdk.capture_exception(e)

    logger.info(f"Screenshot of {page_url} taken: {s3_link}")
    clean_screenshot_driver(selenium_driver, file_path, kill_driver=kill_driver)

    return s3_link


def build_instagram_webshot(ig_window_width, ig_window_height, display_url, html_file_path, selenium_driver=None):

    # Add a random uuid to the file name
    file_path = f"{uuid4()}_webshot.png"

    # We store whether the driver is provided or created within the function (useful to know whether to quit the driver)
    is_driver_provided = True if selenium_driver else False

    s3_link = None

    try:
        # Initialize a driver if needed
        if not selenium_driver:
            selenium_driver = init_screenshot_driver(selenium_driver, domain_name="instagram.com")

        if not selenium_driver.driver:
            selenium_driver.launch_driver()

        selenium_driver.driver.get(f"file:///{os.getcwd()}//{html_file_path}")

        time.sleep(0.5)

        # Make a screenshot of the whole page
        selenium_driver.driver.set_window_position(0, 0)
        selenium_driver.driver.set_window_size(ig_window_width, ig_window_height)

        time.sleep(0.5)

        selenium_driver.driver.save_screenshot(file_path)

        add_date_url_stamp_to_image(file_path, display_url)

        _, s3_link = upload_file_to_s3(
            local_file=file_path,
            bucket=SPECIFIC_SCRAPER_AWS_BUCKET,
            file_name=f"{ENVIRONMENT_NAME}/webshots/{uuid4()}.png",
            file_type="image/png",
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(traceback.format_exc())

    # Kill the driver if it has been created in this function
    # If the driver is provided, killing it is handled outside this function to enable more efficient batching
    kill_driver = not is_driver_provided

    clean_screenshot_driver(selenium_driver, file_path, kill_driver=kill_driver)

    return s3_link


def save_element_screenshot(driver, file_path, element=None, css_selector=None):
    """Make a screenshot of an element in the current page

    We use the property CSS selector only if element is not provided
    """

    if not element:
        element = driver.wait_and_find_element(By.CSS_SELECTOR, css_selector)
    location = element.location
    size = element.size

    driver.set_window_position(location["x"], location["y"])
    driver.set_window_size(driver.get_window_size()["width"], size["height"] + 1000)
    time.sleep(float(ARCHIVING_DEFAULT_SLEEP_AFTER_SET_WINDOW_TO_REQUIRED_SIZE))

    # Scroll a bit towards the top
    driver.execute_script(f"window.scrollTo(0, {location['y'] - 500})")
    time.sleep(float(ARCHIVING_DEFAULT_SCROLL_SLEEP))

    # Get a screenshot of the entire page
    png = driver.get_screenshot_as_png()

    # Use the PIL library to load the image in memory
    im = Image.open(BytesIO(png))

    # Crop the top and the bottom
    width, height = im.size
    left = 0
    right = width
    top = 200
    bottom = height - 200

    im = im.crop((left, top, right, bottom))

    im.save(file_path)


def init_screenshot_driver(selenium_driver=None, domain_name=None):
    if not selenium_driver:
        from selenium_driver.main_driver import Selenium

        selenium_driver = Selenium(domain_name=domain_name)

    if not selenium_driver.driver:
        # TODO: find a way to override config load_images = True
        selenium_driver.launch_driver()

    return selenium_driver


def clean_screenshot_driver(selenium_driver, file_path, kill_driver=True):
    """Cleanup the resources (close the driver and remove the temporary image file)"""

    try:
        # Remove file from local storage
        os.remove(file_path)
    except Exception as ex:
        logger.info(f"Exception on cleaning Screenshot Driver {str(ex)}")
        pass

    if kill_driver is True:
        selenium_driver.kill_driver()
