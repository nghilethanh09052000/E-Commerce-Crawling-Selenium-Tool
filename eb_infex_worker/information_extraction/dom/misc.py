import os.path
import logging
import re
import itertools
from functools import reduce
from typing import Optional, Any, List, Tuple, Dict, Protocol, Literal
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


"""
Helpers for LXML features
"""


CONTROL_CHARS = "".join(map(chr, itertools.chain(range(0x00, 0x20), range(0x7F, 0xA0))))
CONTROL_CHAR_RE = re.compile("[%s]" % re.escape(CONTROL_CHARS))


def remove_control_chars(s):
    """Strip values that can not be present in XML nodes"""
    return CONTROL_CHAR_RE.sub("", s)


def none2str(x):
    return "" if x is None else x


def textclean(x):
    return " ".join(none2str(x).strip().split())


def lxml_text_wtail(node) -> str:
    """
    Text inside lxml nodes that includes children's tails

    https://stackoverflow.com/a/7500304/5208398
    LXML by default only returns text before any children
    Something like <h2><strong>text</strong>More text</h2> is reported as
    having empty text
    """
    if node.text:
        result = node.text
    else:
        result = ""
    for child in node:
        if child.tail is not None:
            result += child.tail
    return result


def get_color_rgba(x):
    r, g, b, a = 0, 0, 0, 0
    if re.match(r"rgba\((\d+), (\d+), (\d+), (\d+)\)", x):
        r, g, b, a = map(int, re.match(r"rgba\((\d+), (\d+), (\d+), (\d+)\)", x).groups())
    elif re.match(r"rgb\((\d+), (\d+), (\d+)\)", x):
        r, g, b = map(int, re.match(r"rgb\((\d+), (\d+), (\d+)\)", x).groups())
    return np.r_[r, g, b, a] / 255


def check_flavour_presence(lxml_rtree, flavours):
    flavours_present = {}
    for flavour in flavours:
        els = lxml_rtree.xpath(f"//*[@data-nv-flavour='{flavour}']")
        assert len(els) in (0, 1), "Multiple nodes have same flavour"
        flavours_present[flavour] = len(els) == 1
    return flavours_present


def kill_helper_attributes(node):
    """
    Kill the attributes that we introduce earlier with JS preprocessing code
    """
    subnodes = node.xpath(".//*")
    for subnode in [node] + subnodes:
        for k, value in subnode.attrib.items():
            if k.startswith("data-nv"):
                del subnode.attrib[k]


def get_label_presence_filter(all_df_metas, lfilter_flavours: Optional[str]) -> Any:
    """Given + separated flavours, query for webpages that contain them all"""
    if lfilter_flavours is not None:
        lfilter_flavours_ = lfilter_flavours.split("+")
        lfilter_flavours__ = [all_df_metas[f] for f in lfilter_flavours_]
        lfilter = reduce(lambda x, y: x & y, lfilter_flavours__)
    else:
        lfilter = all_df_metas.index
    return lfilter


# Working with external data


def load_spreadsheet_file(
    table_path: str,
    folder: str,
    kind: Literal["madagascar", "august2021"],
    flavours=["title", "price", "description", "poster", "image"],
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Open spreadsheet with annotations, parse into a pd.DataFrame
    """
    if kind == "madagascar":
        df_pages = pd.read_excel(table_path, engine="openpyxl")
        df_pages = df_pages.drop([4, 145, 167, 341, 359, 563])  # Bad examples
        df_pages = df_pages[df_pages["QA INNOVATIANA"] == "X"]  # QA approval
        df_pages = df_pages[
            [
                "PAGE_URL",
                "SAVED_PAGE_NAME",
                "TITLE_XPATH",
                "PRICE_XPATH",
                "DESCRIPTION_XPATH",
                "POSTER_NAME_XPATH",
                "IMAGE_XPATH",
            ]
        ]
        df_pages.columns = ["post_url", "file_name", "title", "price", "description", "poster", "image"]
    elif kind == "august2021":
        df_pages = pd.read_excel(table_path, engine="odf")
        good_columns = ["post_url", "file_name"] + [f"post_{x}_path" for x in flavours]
        df_pages = df_pages[good_columns]
    else:
        raise RuntimeError()
    log.debug(f"N pages (Initial): {len(df_pages)}")

    # Title and Image must be present
    df_pages = df_pages[~df_pages["post_title_path"].isna()]
    df_pages = df_pages[~df_pages["post_image_path"].isna()]
    # Assign filepaths, ensure presence
    df_pages["filepath"] = df_pages["file_name"].map(lambda x: os.path.join(folder, x))
    df_pages[df_pages["filepath"].map(os.path.exists)]

    # image_xpath will be called in JS code with doublequotes. Need to cast
    # xpath to single quote when possible
    has_dquote = df_pages["post_image_path"].map(lambda x: '"' in x)
    has_squote = df_pages["post_image_path"].map(lambda x: "'" in x)
    assert not (has_squote & has_dquote).any(), "Can not handle mixed quotes"
    df_pages["post_image_path"] = df_pages["post_image_path"].map(lambda x: x.replace('"', "'"))
    has_squote = df_pages["post_image_path"].map(lambda x: "'" in x)
    log.debug(f"{has_squote.sum()} xpaths with single quotes")
    return df_pages, flavours


def compute_split_inds(iids, split_division, split_names, seed) -> Dict[str, np.ndarray]:
    """
    Divide shuffled iids into splits proportionally to split_division
    """
    split_division = np.array(split_division)
    rgen = np.random.default_rng(seed)
    split_division_nrm = split_division / np.sum(split_division)
    iids_shuf = rgen.permutation(iids)
    split_at = (np.cumsum(split_division_nrm) * len(iids_shuf))[:-1].astype(int)
    iids_per_split = np.array_split(iids_shuf, split_at)
    iids_per_split = dict(zip(split_names, iids_per_split))
    return iids_per_split


# https://github.com/python/mypy/issues/2087
class ConfigAtttribute(Protocol):
    CFG_YML: str


def config_decorator(func: Any) -> ConfigAtttribute:
    return func


@config_decorator
def subsample_df(df, cf):
    # Subsampling for faster evaluation, debugging
    if cf["data.subsampling.size"]:
        df = df.sample(frac=cf["data.subsampling.size"], random_state=cf["data.subsampling.seed"]).sort_index()
    elif cf["data.subsampling.inds"]:
        sinds = cf["data.subsampling.inds"]
        if isinstance(sinds, str):
            with Path(sinds).open("r") as f:
                sinds = list(map(int, f.readline().split(" ")))
        assert isinstance(sinds, list)
        df = df.loc[sinds]
    return df


subsample_df.CFG_YML = """
data:
    subsampling:
        size: ~
        inds: ~
        seed: 84
"""
