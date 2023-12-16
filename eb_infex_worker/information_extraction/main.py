import logging
import time
import traceback
from pathlib import Path
from typing import Dict
import warnings

import lxml.html
from selenium import webdriver  # type: ignore
from selenium.common.exceptions import TimeoutException  # type: ignore
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from eb_infex_worker import logger
from eb_infex_worker.information_extraction.dom.feats import (
    convert_lxml_tree_to_feats, remove_invisible_boxes0,
    tree_features_to_npfeatures)
from eb_infex_worker.information_extraction.dom.js import (sl_driver_get_page,
                                                           sl_start_driver)
from eb_infex_worker.information_extraction.dom.misc import textclean
from eb_infex_worker.information_extraction.dom.trees import lxml_from_string
from eb_infex_worker.information_extraction.js_preprocessing import get_main_script
from eb_infex_worker.information_extraction.pattern_detection.pattern_detector import PatternDetector
from eb_infex_worker.information_extraction.pattern_detection.utils import clean_post_url
from eb_infex_worker.information_extraction.utils.snippets import (ExcFailure,
                                                                   Failure)
from eb_infex_worker.information_extraction.vst import load_pkl

POSTER_PROBA_THRESHOLD = 0.45

PAC, PDC = 5, 50
WINDOW_SIZE = (1920, 1080)
PAGE_TIMEOUT = 30
ELEMENT_TIMEOUT = 10
MAX_RECURSION = 3

# Segmentation parameters
pac = 6
pdc = 60

# Load model
FLAVOURS = ["title", "price", "description", "poster"]
trained_models = {}
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for flavour in FLAVOURS:
        trained_models[flavour] = load_pkl(
            Path(f"eb_infex_worker/information_extraction/models/100__vanilla_trained_models/trained_{flavour}.pkl")
        )

flavours_expanded = ["normal"] + list(trained_models.keys()) + ["image"]

FEATURE_KEYS = [
    "imnode_distance",
    "depth",
    "height",
    "currency_detected",
    "len_text_clean",
    "len_text_content",
    "ratio_digits_characters",
    "tags_present",
    "h_title_value",
    "image_tag",
    "list_table_form_tag",
    "flow_tag",
    "phrasing_tag",
    "palpable_tag",
    "list_table_form_parent_tag",
    "price_in_attributes",
    "image_dist",
    "x",
    "y",
    "w",
    "h",
    "visible",
    "capital_percentage",
    "fontsize",
    "line_through",
    "color_diff",
    "bg_color",
]


def scroll_down_smoothly(driver):
    is_at_bottom = False
    time_scroll_action = 3
    scroll_tolerance_action = 100
    scroll_sleep = 0.1
    max_scroll = 10
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


def infex_single_website(
    page_url: str,
    image_url: str,
    image_s3_url: str = None,
    recursion=0,
    scroll_smoothly: bool = False,
    js_postprocess: bool = False,  # Perform segmentation+merge in JS code
    remove_invisible_boxes: bool = True,  # Remove invisible DOM elements
    other_xpaths: Dict[str, str] = {},  # Useful for postfactum flavour access (i.e. during evaluation)
    page_timeout_override: int = None,
    element_timeout_override: int = None,
    use_navee_driver=False,
):

    if use_navee_driver:

        # This import needs to be here for this module to work with Navee Driver
        from app.utils.navee_driver import get_navee_driver_infex_results

        return get_navee_driver_infex_results(
            page_url,
            image_url,
            image_s3_url=image_s3_url,
            recursion=recursion,
            scroll_smoothly=scroll_smoothly,
            js_postprocess=js_postprocess,
            remove_invisible_boxes=remove_invisible_boxes,
            other_xpaths=other_xpaths,
            page_timeout_override=page_timeout_override,
            element_timeout_override=element_timeout_override,
        )

    page_timeout = page_timeout_override or PAGE_TIMEOUT
    element_timeout = element_timeout_override or ELEMENT_TIMEOUT

    logger.info("Starting to run infex_single_website")

    if js_postprocess:
        do_segment, do_merge = 1, 1
    else:
        do_segment, do_merge = 0, 0

    # Part with selenium driver
    try:
        try:
            driver = sl_start_driver(WINDOW_SIZE)
            sl_driver_get_page(driver, page_url, WINDOW_SIZE, page_timeout, element_timeout)

            if scroll_smoothly:
                scroll_down_smoothly(driver)
        except TimeoutException:
            logging.info("Page load Timeout Occured ... moving to next instructions")

        # Find image xpathhtml_doc = driver.page_source
        html_doc = driver.page_source
        pattern_detected, image_xpath, final_node, new_links = PatternDetector().search_pattern(
            html_doc, driver.current_url if driver.current_url else page_url, image_url, image_s3_url
        )

        if image_xpath is None:
            logging.info("End: image not found in web page")
            if "driver" in locals():
                driver.quit()
            return None, None, None, None, None, pattern_detected, "image not found in web page"

        if pattern_detected and recursion < MAX_RECURSION:
            for new_link in new_links:
                new_page_url, title, price, description, poster, pattern_detected, error = infex_single_website(
                    page_url=new_link,
                    image_url=image_url,
                    image_s3_url=image_s3_url,
                    recursion=recursion + 1,
                    scroll_smoothly=scroll_smoothly,
                )

                if new_page_url:
                    logging.info(f"End: data found on new link: {new_page_url}")
                    if "driver" in locals():
                        driver.quit()
                    return new_page_url, title, price, description, poster, pattern_detected, error

        image_xpath = image_xpath.replace("\n", "\\n").replace("\r", "\\r")
        image_xpath = image_xpath.replace('"', '\\"')

        # Assign the image flavour
        other_xpaths["image"] = image_xpath
        for flavour, xpath in other_xpaths.items():
            el = driver.find_element(by=By.XPATH, value=xpath)
            driver.execute_script(f"arguments[0].setAttribute('data-nv-flavour', '{flavour}')", el)

        # Execute js preprocessing script
        script = get_main_script()
        res = driver.execute_script(
            script
            + '\n\nreturn task_page_preprocessing({}, {},  "{}", {}, {})'.format(
                do_segment, do_merge, image_xpath, PAC, PDC
            )
        )

        if res is None:
            if "driver" in locals():
                driver.quit()
            raise ExcFailure("JS script failed to reach image_xpath and returned None", image_xpath=image_xpath)

    except Exception as e:
        logging.error(f"Error on preprocessing image: {e}")

        if "driver" in locals():
            driver.quit()

        return None, None, None, None, None, None, traceback.format_exc()

    try:
        # Catch URL redirections
        driver_current_url = driver.current_url

        if "driver" in locals():
            driver.quit()

    except Exception:
        driver_current_url = page_url
    # End of the Selenium driver part

    try:
        if page_url != driver_current_url:  # get url redirects
            logging.warning(f"Page redirects from: {page_url} to: {driver_current_url}")
            page_url = driver_current_url

        if not pattern_detected:  # clean post url
            page_url = clean_post_url(page_url)

    except Exception as ex:
        logging.warning(f"Error on cleaning post url {str(ex)}")

    lxml_root = lxml.etree.HTML(res)
    tree_string = lxml.etree.tostring(lxml_root, pretty_print=True)

    # // Extract features from the tree
    tree_features = convert_lxml_tree_to_feats(tree_string, flavours_expanded)
    if isinstance(tree_features, Failure):
        raise ExcFailure(f"Failed feature extraction at {page_url}. Failure: {tree_features.message}")
    if remove_invisible_boxes:
        tree_features = remove_invisible_boxes0(tree_features)

    # // Convert to numpy
    npfeatures, metadf = tree_features_to_npfeatures(tree_features, FEATURE_KEYS)

    predicted = {}
    for flavour, trained_model in trained_models.items():
        # Load the model
        if set(trained_model["feature_keys"]) != set(FEATURE_KEYS):
            logging.warning("Model was trained on different features")
        # // Apply MLP model on the features
        X = trained_model["scaler"].transform(npfeatures)
        proba = trained_model["clf"].predict_proba(X)[:, 1]
        predicted_index = proba.argmax()
        predicted_proba = proba[predicted_index]
        # // This corresponds to following tree node
        predicted_node_features = tree_features[predicted_index]
        predicted_xpath = predicted_node_features["_xpath"]
        # // That has the following LXML node
        lxml_root, lxml_rtree = lxml_from_string(tree_string)
        predicted_lxml_node = lxml_rtree.xpath(predicted_xpath)[0]
        predicted_text = textclean(predicted_lxml_node.text_content())  # test
        predicted[flavour] = {
            "xpath": str(predicted_xpath),
            "text": str(predicted_text),
            "proba": float(predicted_proba),
        }

    title = predicted["title"]["text"]
    price = predicted["price"]["text"]
    description = predicted["description"]["text"]
    poster = (
        predicted["poster"]["text"]
        if (predicted["poster"]["proba"] > POSTER_PROBA_THRESHOLD and len(predicted["poster"]["text"]) <= 20)
        else None
    )

    return page_url, title, price, description, poster, pattern_detected, None


if __name__ == "__main__":

    logger.input("Start: infex_single_website")

    (extracted_page_url, title, price, description, poster, pattern_detected, infex_error,) = infex_single_website(
        page_url="http://books.toscrape.com/",
        image_url="http://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
    )

    print(f"URL: {extracted_page_url}")
    print(f"Title: {title}")
    print(f"Price: {price}")
    print(f"Description: {description}")
    print(f"Poster: {poster}")
    print(f"Pattern detected: {pattern_detected}")
    print(f"Infex error: {infex_error}")

    logger.output("End: infex_single_website")
