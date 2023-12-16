import copy
import logging
import traceback
from io import BytesIO
from PIL import Image
from typing import Optional

import cv2
import numpy as np
import pandas as pd

import selenium.webdriver

log = logging.getLogger(__name__)


"""
Box routines

https://github.com/vsydorov/beyond_keyframes/blob/master/thes/data/tubes/routines.py
"""


def _barea(box):
    return np.prod(box[2:] - box[:2])


def _bareas(boxes):
    return np.prod(boxes[..., 2:] - boxes[..., :2], axis=1)


def _inter_areas(boxes1, boxes2):
    inter = np.c_[np.maximum(boxes1[..., :2], boxes2[..., :2]), np.minimum(boxes1[..., 2:], boxes2[..., 2:])]
    inter_subs = inter[..., 2:] - inter[..., :2]
    inter_areas = np.prod(inter_subs, axis=1)
    inter_areas[(inter_subs < 0).any(axis=1)] = 0.0
    return inter_areas


def numpy_iou_N1(boxes1, box2):
    assert len(boxes1.shape) == 2
    assert boxes1.shape[-1] == 4
    assert box2.shape == (4,)
    inter_areas = _inter_areas(boxes1, box2)
    boxes1_areas = _bareas(boxes1)
    box2_area = _barea(box2)
    union_areas = boxes1_areas + box2_area - inter_areas
    ious = inter_areas / union_areas
    return ious


def numpy_inner_overlap_N1(boxes1, box2):
    assert len(boxes1.shape) == 2
    assert boxes1.shape[-1] == 4
    assert box2.shape == (4,)
    inter_areas = _inter_areas(boxes1, box2)
    boxes1_areas = _bareas(boxes1)
    ioverlaps = inter_areas / boxes1_areas
    return ioverlaps


"""
Selenium
"""


def sl_screen_pil(driver):
    x = driver.get_screenshot_as_png()
    x = BytesIO(x)
    img = Image.open(x)
    return img


def sl_screen_ocv(driver):
    x = driver.get_screenshot_as_png()
    x = np.fromstring(x, np.uint8)
    img = cv2.imdecode(x, cv2.IMREAD_COLOR)
    return img


def save_fullpage_screenshot(driver: selenium.webdriver.Chrome, path: Optional[str] = None):
    """
    https://stackoverflow.com/a/52572919/5208398
    """
    original_size = driver.get_window_size()
    required_width = driver.execute_script("return document.body.parentNode.scrollWidth")
    required_height = driver.execute_script("return document.body.parentNode.scrollHeight")
    driver.set_window_size(required_width, required_height)
    # driver.save_screenshot(path)  # has scrollbar
    el = driver.find_element_by_tag_name("body")
    screen = el.screenshot_as_png
    driver.set_window_size(original_size["width"], original_size["height"])
    screen = np.fromstring(screen, np.uint8)
    screen = cv2.imdecode(screen, cv2.IMREAD_COLOR)
    if path:
        cv2.imwrite(path, screen)
    return screen


"""
MISC
"""


def pdtrue(s: pd.Series):
    """Indices of true elements"""
    return s[s].index.values


class ExcFailure(Exception):
    def __init__(self, message, **kwargs):
        self.message = message
        self.kwargs = kwargs


class Failure(object):
    def __init__(self, message, **kwargs):
        self.message = message
        self.kwargs = kwargs


def to_traceback(failure):
    e = failure.kwargs.get("e", None)
    if isinstance(e, Exception):
        failure = copy.deepcopy(failure)
        del failure.kwargs["e"]
        failure.kwargs["e_traceback"] = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    return failure


def handle_excfailure(e, add_kwargs={}):
    if isinstance(e, ExcFailure):
        failure = Failure(e.message, **add_kwargs, **e.kwargs)
    else:
        failure = Failure("Unexpected exception", **add_kwargs)
    failure = to_traceback(failure)  # Make picklable
    str_kwargs = "\n".join(f"{k}: {v}" for k, v in failure.kwargs.items())
    log.info(f"Error: {failure.message}\n{str_kwargs}")
    return failure
