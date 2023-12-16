import logging
from typing import Dict, Optional, Tuple, Union

import lxml.etree
import lxml.html
import pandas as pd
import selenium.webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By

from eb_infex_worker.information_extraction.dom.misc import check_flavour_presence
from eb_infex_worker.information_extraction.dom.trees import lxml_from_string
from eb_infex_worker.information_extraction.js_preprocessing import get_main_script
from eb_infex_worker.information_extraction.utils.snippets import (
    ExcFailure, Failure, handle_excfailure)

log = logging.getLogger(__name__)


# JS preprocessing


def flavour_check_assign_selv2(driver, flavour_xpaths, prefix=""):
    """
    Uses selenium to check for flavours and assign data-nv-flavour attributes
    """
    flavours_present = {flavour: False for flavour in flavour_xpaths}
    flavour_elements = {}
    for flavour, xpath in flavour_xpaths.items():
        if not xpath:
            continue
        # Find via classname (priority)
        try:
            el_class = driver.find_element_by_class_name(f"navee_post_{flavour}")
        except NoSuchElementException:
            el_class = None
        # Find via xpath (lower priority)
        try:
            el_xpath = driver.find_element(by=By.XPATH, value=xpath)
        except NoSuchElementException:
            el_xpath = None
        # Select element. Classname has higher priority
        if el_class:
            el = el_class
            if el_class != el_xpath:
                log.debug(f"At {prefix}/{flavour} el_class != el_xpath. " "Taking el_class")
        elif el_xpath:
            el = el_xpath
            if el_class != el_xpath:
                log.debug(f"At {prefix}/{flavour} el_class is broken. " "Taking el_xpath")
        else:
            log.debug(f"At {prefix}/{flavour} can not access element. {xpath}")
            continue
        # Assign data-nv-flavour
        driver.execute_script(f"arguments[0].setAttribute('data-nv-flavour', '{flavour}')", el)
        flavours_present[flavour] = True
        flavour_elements[flavour] = el
    return flavours_present, flavour_elements


def sl_start_driver(window_size):
    options = selenium.webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-ssl-errors=yes")
    options.add_argument("--ignore-certificate-errors")

    if window_size is not None:
        wW, wH = window_size
        options.add_argument(f"--window-size={wW}x{wH}")
    driver = selenium.webdriver.Chrome(chrome_options=options)

    return driver


def sl_driver_get_page(
    driver: selenium.webdriver.Chrome,
    page_path: str,
    window_size: Optional[Tuple[int, int]],
    page_timeout: int,
    element_timeout: int,
):
    driver.set_page_load_timeout(page_timeout)
    driver.implicitly_wait(page_timeout)
    try:
        driver.get(page_path)
    except TimeoutException:
        raise ExcFailure("Page load timeout")
    if window_size is not None:
        wW, wH = window_size
        driver.set_window_size(wW, wH)
    driver.set_page_load_timeout(element_timeout)
    driver.implicitly_wait(element_timeout)


def sl_driver_get_flavours_and_clean(driver, row_id, page_path, flavour_xpaths):
    # Assign flavors via js
    flavours_present, flavour_elements = flavour_check_assign_selv2(driver, flavour_xpaths, f"{row_id}/{page_path}")
    if not flavours_present["image"]:
        raise ExcFailure("Image flavour absent", flavours_present=flavours_present)
    # Clean "navee_post_*" class, thus removing CSS highlighting Dana introduced
    for flavour, el in flavour_elements.items():
        attr_class = el.get_attribute("class")
        nattr_class = " ".join([x for x in attr_class.split(" ") if not x.startswith("navee_post")])
        driver.execute_script(f"arguments[0].setAttribute('class', '{nattr_class}')", el)
    return flavours_present


def sl_driver_execute_js(
    driver: selenium.webdriver.Chrome,
    flavours_present,
    flavour_xpaths,
    do_segment,
    do_merge,
    pac,
    pdc,
    ensure_stable_flavours,
):

    # Execute js preprocessing script
    script = get_main_script()
    doc = driver.execute_script(script + "\n\nreturn get_serialized_document()")
    lxml_root = lxml.etree.HTML(doc)
    n_before = len(lxml_root.xpath(".//*"))
    image_xpath = flavour_xpaths["image"]
    res = driver.execute_script(
        script
        + '\n\nreturn task_page_preprocessing({}, {},  "{}", {}, {})'.format(
            int(do_segment), int(do_merge), image_xpath, pac, pdc
        )
    )
    if res is None:
        raise ExcFailure("JS script failed to reach image_xpath and returned None", image_xpath=image_xpath)
    lxml_root = lxml.etree.HTML(res)
    tree_string = lxml.etree.tostring(lxml_root, pretty_print=True)
    # Reload the lxml to get accurate number of nodes (after JS processing)
    lxml_root2, lxml_rtree2 = lxml_from_string(tree_string)
    n_after = len(lxml_root2.xpath(".//*"))

    # Check presence of all previously flavoured nodes
    flavours_present_after_js = check_flavour_presence(lxml_root2.getroottree(), flavour_xpaths.keys())
    if flavours_present != flavours_present_after_js:
        change = pd.DataFrame.from_dict(
            {"before": flavours_present, "after": flavours_present_after_js}, orient="index"
        )
        MSG = "Flavour presence changed after js"
        if ensure_stable_flavours:
            raise ExcFailure(MSG, change=change)
        else:
            log.warn(f"{MSG}: {change}")

    # Should not happen
    if not flavours_present_after_js["image"]:
        raise ExcFailure(
            "Image flavour absent after processing",
            flavours_present=flavours_present,
            flavours_present_after_js=flavours_present_after_js,
        )

    page_result = {
        "tree_string": tree_string,
        "n_before": n_before,
        "n_after": n_after,
        "flavours_present": flavours_present_after_js,
    }
    return page_result


def js_preprocess_to_lxml(
    row_id: int,
    filepath: str,
    flavour_xpaths: Dict[str, str],
    do_segment: bool,
    do_merge: bool,
    pac: int,
    pdc: int,
    window_size: Optional[Tuple[int, int]],
    page_timeout: int,
    element_timeout: int,
    ensure_stable_flavours: bool,
) -> Union[Dict, Failure]:
    """
    Execute js_function that assigns CSS values to DOM nodes, convert to LXML
    parsable string

    Args:
        row_id: index of the webpage
        page_page: path on local disk to saved webpage
        flavour_xpaths: xpath to annotated DOM nodes
        do_segment: segment "main content" according to cite:vargas2015web
        do_merge: merge single parent-children DOM nodes (Mathieu's implementation)
        pac, pdc: params for "main content" segmentation
        window_size: resize selenium window to this size
    """
    driver = None
    page_path = f"file://{filepath}"
    try:
        driver = sl_start_driver(window_size)
        sl_driver_get_page(driver, page_path, window_size, page_timeout, element_timeout)
        flavours_present = sl_driver_get_flavours_and_clean(driver, row_id, page_path, flavour_xpaths)
        page_result = sl_driver_execute_js(
            driver, flavours_present, flavour_xpaths, do_segment, do_merge, pac, pdc, ensure_stable_flavours
        )
    except Exception as e:
        add_kwargs = dict(row_id=row_id, page_path=page_path, flavour_xpaths=flavour_xpaths)
        failure = handle_excfailure(e, add_kwargs)
        return failure

    finally:
        if driver is not None:
            driver.quit()
    return page_result
