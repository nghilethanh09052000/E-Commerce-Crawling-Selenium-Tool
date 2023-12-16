"""
Extract features from LXML/Selenium nodes
"""
import itertools
import logging
import re
import math
from typing import List, Dict, Tuple, Union, TypedDict
from pathlib import Path

import regex
import networkx as nx
import numpy as np
import pandas as pd

import eb_infex_worker.information_extraction.vst as vst

from eb_infex_worker.information_extraction.dom.misc import textclean, get_color_rgba, lxml_text_wtail
from eb_infex_worker.information_extraction.dom.trees import create_annotated_nx_tree
from eb_infex_worker.information_extraction.utils.snippets import Failure

log = logging.getLogger(__name__)


# source: https://www.w3schools.com/tags/ref_byfunc.asp
FORMATTING_TAGS = [
    "acronym",
    "abbr",
    "address",
    "b",
    "bdi",
    "bdo",
    "big",
    "blockquote",
    "center",
    "cite",
    "code",
    "del",
    "dfn",
    "em",
    "font",
    "i",
    "ins",
    "kbd",
    "mark",
    "meter",
    "pre",
    "progress",
    "q",
    "rp",
    "rt",
    "ruby",
    "s",
    "samp",
    "small",
    "strike",
    "strong",
    "sub",
    "sup",
    "template",
    "time",
    "tt",
    "u",
    "var",
    "wbr",
]
FORMS_AND_INPUT_TAGS = [
    "form",
    "input",
    "textarea",
    "button",
    "select",
    "optgroup",
    "option",
    "label",
    "fieldset",
    "legend",
    "datalist",
    "output",
]
FRAME_IMAGES_AND_AUDIO_TAGS = [
    "frame",
    "frameset",
    "noframes",
    "iframe",
    "img",
    "map",
    "area",
    "canvas",
    "figcaption",
    "figure",
    "picture",
    "svg",
    "audio",
    "source",
    "track",
    "video",
    "embed",
    "applet",
]
LIST_TAGS = ["ul", "ol", "li", "dir", "dl", "dt", "dd"]
TABLE_TAGS = ["table", "caption", "th", "tr", "td", "thead", "tbody", "tfoot", "col", "colgroup"]


# source: https://tel.archives-ouvertes.fr/tel-01128002/document
METADATA_CONTENT_TAGS = ["base", "link", "meta", "noscript", "script", "style", "template", "title"]
FLOW_CONTENT_TAGS = [
    "a",
    "abbr",
    "address",
    "article",
    "aside",
    "audio",
    "b",
    "bdi",
    "bdo",
    "blockquote",
    "br",
    "button",
    "canvas",
    "cite",
    "code",
    "data",
    "datalist",
    "del",
    "dfn",
    "div",
    "dl",
    "em",
    "embed",
    "fieldset",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "keygen",
    "label",
    "main",
    "map",
    "mark",
    "math",
    "meter",
    "nav",
    "noscript",
    "object",
    "ol",
    "output",
    "p",
    "pre",
    "progress",
    "q",
    "ruby",
    "s",
    "samp",
    "script",
    "section",
    "select",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "svg",
    "table",
    "template",
    "textarea",
    "time",
    "u",
    "ul",
    "var",
    "video",
    "wbr",
    "text",
]
PHRASING_CONTENT_TAGS = [
    "a",
    "abbr",
    "audio",
    "b",
    "bdi",
    "bdo",
    "br",
    "button",
    "canvas",
    "cite",
    "code",
    "data",
    "datalist",
    "del",
    "dfn",
    "em",
    "embed",
    "i",
    "iframe",
    "img",
    "input",
    "ins",
    "kbd",
    "keygen",
    "label",
    "map",
    "mark",
    "math",
    "meter",
    "noscript",
    "object",
    "output",
    "progress",
    "q",
    "ruby",
    "s",
    "samp",
    "script",
    "select",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "svg",
    "template",
    "textarea",
    "time",
    "u",
    "var",
    "video",
    "wbr",
    "text",
]
PALPABLE_CONTENT_TAGS = [
    "a",
    "abbr",
    "address",
    "article",
    "aside",
    "b",
    "bdi",
    "bdo",
    "blockquote",
    "button",
    "canvas",
    "cite",
    "code",
    "data",
    "dfn",
    "div",
    "em",
    "embed",
    "fieldset",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "i",
    "iframe",
    "img",
    "ins",
    "kbd",
    "keygen",
    "label",
    "main",
    "map",
    "mark",
    "math",
    "meter",
    "nav",
    "object",
    "output",
    "p",
    "pre",
    "progress",
    "q",
    "ruby",
    "s",
    "samp",
    "section",
    "select",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "svg",
    "table",
    "textarea",
    "time",
    "u",
    "var",
    "video",
]
MOST_PRESENT_TAGS = ["div", "span", "a", "img", "i", "option", "input", "p"]
SAFE_CURRENCY_SYMBOLS = [
    # Variants of $, etc. They need to be before $.
    "Bds$",
    "CUC$",
    "MOP$",
    "AR$",
    "AU$",
    "BN$",
    "BZ$",
    "CA$",
    "CL$",
    "CO$",
    "CV$",
    "HK$",
    "MX$",
    "NT$",
    "NZ$",
    "TT$",
    "RD$",
    "WS$",
    "US$",
    "$U",
    "C$",
    "J$",
    "N$",
    "R$",
    "S$",
    "T$",
    "Z$",
    "A$",
    "SY£",
    "LB£",
    "CN¥",
    "GH₵",
    # unique currency symbols
    "$",
    "€",
    "£",
    "zł",
    "Zł",
    "Kč",
    "₽",
    "¥",
    "￥",
    "฿",
    "դր.",
    "դր",
    "₦",
    "₴",
    "₱",
    "৳",
    "₭",
    "₪",
    "﷼",
    "៛",
    "₩",
    "₫",
    "₡",
    "টকা",
    "ƒ",
    "₲",
    "؋",
    "₮",
    "नेरू",
    "₨",
    "₶",
    "₾",
    "֏",
    "ރ",
    "৲",
    "૱",
    "௹",
    "₠",
    "₢",
    "₣",
    "₤",
    "₧",
    "₯",
    "₰",
    "₳",
    "₷",
    "₸",
    "₹",
    "₺",
    "₼",
    "₾",
    "₿",
    "ℳ",
    "ر.ق.\u200f",
    "د.ك.\u200f",
    "د.ع.\u200f",
    "ر.ع.\u200f",
    "ر.ي.\u200f",
    "ر.س.\u200f",
    "د.ج.\u200f",
    "د.م.\u200f",
    "د.إ.\u200f",
    "د.ت.\u200f",
    "د.ل.\u200f",
    "ل.س.\u200f",
    "د.ب.\u200f",
    "د.أ.\u200f",
    "ج.م.\u200f",
    "ل.ل.\u200f",
    " تومان",
    "تومان",
    # other common symbols, which we consider unambiguous
    "EUR",
    "euro",
    "eur",
    "CHF",
    "DKK",
    "Rp",
    "lei",
    "руб.",
    "руб",
    "грн.",
    "грн",
    "дин.",
    "Dinara",
    "динар",
    "лв.",
    "лв",
    "р.",
    "тңг",
    "тңг.",
    "ман.",
]
SYMBOLS_REGEX = re.compile("|".join(re.escape(s) for s in SAFE_CURRENCY_SYMBOLS))


DomColor = Tuple[float, float, float, float]


class Domfeature(TypedDict):
    _xpath: str
    _flavour_id: int
    imnode_distance: int
    depth: int
    height: int
    currency_detected: bool
    len_text_clean: int
    len_ttext: int
    len_text_content: int
    ratio_digits_characters: float
    capital_percentage: float
    price_in_attributes: bool
    tags_present: bool
    h_title_value: int
    image_tag: bool
    list_table_form_tag: bool
    flow_tag: bool
    phrasing_tag: bool
    palpable_tag: bool
    list_table_form_parent_tag: bool
    visible: bool
    line_through: bool
    fontsize: float
    color: DomColor
    color_diff: DomColor
    bg_color: DomColor
    bg_color_diff: DomColor
    image_dist: int
    x: float
    y: float
    w: float
    h: float
    x_orig: float
    y_orig: float
    w_orig: float
    h_orig: float
    page_width: float
    page_height: float


def feat_nice_attributes(node):
    nice_attributes = {}
    for k, v in node.attrib.items():
        if (not k.startswith("data-nv-")) and (k not in ["src", "href", "bomtype"]):
            nice_attributes[k] = v
    return nice_attributes


def _get_parent_tags(node):
    tags = []
    while node is not None:
        tags.append(node.tag.lower())
        node = node.getparent()
    return tags


def _get_h_title_value(tag_name):
    for i in range(1, 7):
        if tag_name == "h{}".format(i):
            return 1 - (i - 1) * 0.17
    return 0


def _is_currency_visible(text):
    if SYMBOLS_REGEX.search(text):
        return True
    elif regex.search(r"\p{Sc}", text):
        return True
    return False


def _get_ratio_digits_characters(text):
    len_text_without_whitespace = len("".join(text.split()))
    nb_digits = sum(c.isdigit() for c in text)

    if not len_text_without_whitespace:
        return 0

    return nb_digits / len_text_without_whitespace


def _get_capital_percentage_node(node, text):
    if node.get("data-nv-css-texttransform") == "uppercase":
        capitals_percentage = 1.0
    else:
        capitals_percentage = [char.isupper() for char in text if char.isalpha()]
        capitals_percentage = np.mean(capitals_percentage) if len(capitals_percentage) > 0 else 0
    return capitals_percentage


def _feat_compute_distance(image_x, image_y, x, y, image_w, image_h, w, h, page_width, page_height):
    ixiyxy = np.c_[image_x, image_y, x, y]
    BAD = (ixiyxy < 0).any()
    BAD |= (ixiyxy > np.tile([page_width, page_height], 2)).any()
    BAD |= (ixiyxy < 1).any()
    if BAD:
        dist = 150
    else:
        x_dist = (
            min(abs(x + w - image_x), abs(image_x + image_w - x))
            if (image_x <= x <= image_x + image_w or x <= image_x <= x + w)
            else 0
        )
        y_dist = (
            min(abs(y + h - image_y), abs(image_y + image_h - y))
            if (image_y <= y <= image_y + image_h or y <= image_y <= y + h)
            else 0
        )
        dist = math.sqrt((x_dist ** 2) + (y_dist ** 2))
    return dist


# Trees to Features


def convert_lxml_tree_to_feats(tree_string, FLAVOURS) -> Union[Failure, List[Domfeature]]:
    """
    Convert every DOM node in LXML tree into Domfeature

    - Domfeature is trivially converted into float numpy array
    - Can be processed with an sklearn algorithm afterwards
    """
    nx_tree, lxml_root, lxml_rtree = create_annotated_nx_tree(tree_string)

    # Make sure at least one node is present
    if not len(lxml_root.xpath(".//*")):
        return Failure("No lxml nodes present")
    # Get image node
    try:
        lxml_node_image = lxml_root.xpath("//*[@data-nv-flavour='image']")[0]
        xpath_node_image = lxml_rtree.getpath(lxml_node_image)
    except IndexError:
        return Failure("Can not get image node")
    # Compute distances to image node
    for k, v in nx.shortest_path_length(nx_tree.to_undirected(), xpath_node_image).items():
        nx_tree.nodes[k]["imnode_distance"] = v

    image_x = float(lxml_node_image.get("data-nv-x", 0))
    image_y = float(lxml_node_image.get("data-nv-y", 0))
    image_w = float(lxml_node_image.get("data-nv-w", 0))
    image_h = float(lxml_node_image.get("data-nv-h", 0))

    font_sizes_ = []
    for node in lxml_root.xpath(".//*"):
        if re.match(r"(\d+)px", node.get("data-nv-css-fontsize", "")):
            fsize = int(re.match(r"(\d+)px", node.get("data-nv-css-fontsize", "")).group(1))
            if len(textclean(node.text)):
                font_sizes_.extend([fsize] * len(textclean(node.text)))
    font_sizes = np.array(font_sizes_)
    font_sizes = font_sizes[font_sizes > 0]
    if len(font_sizes):
        median_font_size = np.median(font_sizes)
    else:
        median_font_size = 12

    heights = []
    widths = []
    for node in lxml_root.xpath(".//*"):
        widths.append(float(node.get("data-nv-w", 0)))
        heights.append(float(node.get("data-nv-h", 0)))
    page_width = max(widths)
    page_height = max(heights)

    nodes = lxml_root.xpath(".//*")
    colors = np.vstack([get_color_rgba(n.get("data-nv-css-color", "")) for n in nodes])
    if len(colors):
        median_color = np.nan_to_num(np.median(colors, axis=0))
    else:
        median_color = np.r_[0, 0, 0, 0]

    bg_colors = np.vstack([get_color_rgba(n.get("data-nv-css-backgroundcolor", "")) for n in nodes])
    bg_colors = bg_colors[(bg_colors > 0).any(axis=1)]
    if len(bg_colors):
        median_bg_color = np.nan_to_num(np.median(bg_colors, axis=0))
    else:
        median_bg_color = np.r_[0, 0, 0, 0]

    tree_features = []
    for node in lxml_root.xpath(".//*"):
        node_xpath = lxml_rtree.getpath(node)
        # Text features
        node_text_clean = textclean(node.text)
        node_ttext = lxml_text_wtail(node)
        node_text_content = textclean(node.text_content())
        nice_attributes = feat_nice_attributes(node)
        attributes_text = " ".join(nice_attributes.values()).lower()
        # Tag features
        tag = node.tag.lower()
        parent_tags = _get_parent_tags(node)
        # CSS features
        line_through = (
            (tag == "del") or ("del" in parent_tags) or (node.get("data-nv-css-textdecorationline") == "line-through")
        )
        if re.match(r"(\d+)px", node.get("data-nv-css-fontsize", "")):
            fontsize = float(re.match(r"(\d+)px", node.get("data-nv-css-fontsize", "")).group(1)) / median_font_size
        else:
            fontsize = 1.0
        color = get_color_rgba(node.get("data-nv-css-color", ""))
        bg_color = get_color_rgba(node.get("data-nv-css-backgroundcolor", ""))
        # Distance features
        x = float(node.get("data-nv-x", 0))
        y = float(node.get("data-nv-y", 0))
        w = float(node.get("data-nv-w", 0))
        h = float(node.get("data-nv-h", 0))
        image_dist = int(
            _feat_compute_distance(image_x, image_y, x, y, image_w, image_h, w, h, page_width, page_height)
        )
        if page_width > 1 and page_height > 1:
            norm_x = x / page_width
            norm_y = y / page_height
            norm_w = w / page_width
            norm_h = h / page_height
        else:
            norm_x, norm_y, norm_w, norm_h = 0, 0, 0, 0
        feats: Domfeature = {
            "_xpath": node_xpath,
            "_flavour_id": FLAVOURS.index(node.get("data-nv-flavour", "normal")),
            "imnode_distance": nx_tree.nodes[node_xpath]["imnode_distance"],
            "depth": nx_tree.nodes[node_xpath]["depth"],
            "height": nx_tree.nodes[node_xpath]["height"],
            # Text features
            "currency_detected": _is_currency_visible(node_text_content),
            "len_text_clean": len(node_text_clean),
            "len_ttext": len(node_ttext),
            "len_text_content": len(node_text_content),
            "ratio_digits_characters": _get_ratio_digits_characters(node_text_content),
            "capital_percentage": _get_capital_percentage_node(node, node_text_content),
            "price_in_attributes": "price" in attributes_text,
            # Tag features
            "tags_present": np.isin(MOST_PRESENT_TAGS, tag),
            "h_title_value": _get_h_title_value(tag),
            "image_tag": tag in FRAME_IMAGES_AND_AUDIO_TAGS,
            "list_table_form_tag": tag in (LIST_TAGS + TABLE_TAGS + FORMS_AND_INPUT_TAGS),
            "flow_tag": tag in FLOW_CONTENT_TAGS,
            "phrasing_tag": tag in PHRASING_CONTENT_TAGS,
            "palpable_tag": tag in PALPABLE_CONTENT_TAGS,
            "list_table_form_parent_tag": len(list(set(parent_tags) & {"footer", "nav"})) >= 1,
            # CSS features
            "visible": node.get("data-nv-visible") == "true",
            "line_through": line_through,
            "fontsize": fontsize,
            "color": color,
            "color_diff": np.abs(median_color - color),
            "bg_color": bg_color,
            "bg_color_diff": np.abs(median_bg_color - bg_color),
            # Distance features
            "image_dist": image_dist,
            "x": norm_x,
            "y": norm_y,
            "w": norm_w,
            "h": norm_h,
            # Original location features
            "x_orig": x,
            "y_orig": y,
            "w_orig": w,
            "h_orig": h,
            "page_width": page_width,
            "page_height": page_height,
        }
        tree_features.append(feats)
    return tree_features


def convert_lxml_trees_to_features(
    tree_strings: pd.Series,
    nflavours,
    temp_fold: Path,
    num_workers=0,
) -> Dict[int, List[Domfeature]]:
    """
    Convert nx_tree nodes to featurenodes
    - Uses both LXML and Selenium metadata

    Return: dictionary of list of features indexed by row_id
    """
    # ProcessPool much faster than ThreadingPool
    prepared_args = [(x, nflavours) for x in tree_strings]
    isaver_values = vst.isave.Isaver_fast(
        temp_fold,
        prepared_args,
        convert_lxml_tree_to_feats,
        async_kind="process",
        num_workers=num_workers,
        progress="tree_to_features",
    ).run()
    trees_features = dict(zip(tree_strings.index, isaver_values))
    filtered_trees_features = {}
    for k, v in trees_features.items():
        if isinstance(v, Failure):
            log.warn(f"Bad feature at {k}, possible corrupt data:\n{v.message}")
        else:
            filtered_trees_features[k] = v
    return filtered_trees_features


# Features to numpy array


def _pick_all_features(trees_features):
    present_fkeys = next(iter(next(iter(trees_features.values())))).keys()
    # Simply exclude _meta tag
    good_fkeys = [fk for fk in present_fkeys if fk not in ["_meta"]]
    return good_fkeys


def select_feature_keys_v2(ftake):
    fnames = {}
    fnames["previous"] = [
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
    ]
    fnames["previous+visible"] = fnames["previous"] + ["visible"]
    fnames["mathieu"] = fnames["previous+visible"] + ["capital_percentage", "fontsize", "line_through"]
    fnames["mathieu+color_diffs"] = fnames["mathieu"] + ["color_diff", "bg_color"]  # Oldstyle, should give 80% on price
    fnames["mathieu+all_colors"] = fnames["mathieu+color_diffs"] + ["bg_color_diff"]
    # These have bad perf, since they use "bg_color_diff" and "len_ttext"
    fnames["mathieu+color_diffs+len_ttext"] = fnames["mathieu+color_diffs"] + ["len_ttext"]
    fnames["mathieu+bad_color_diffs"] = fnames["mathieu"] + ["color_diff", "bg_color_diff"]
    # What we had as "mathieu+color_diffs" in new (broken) commits
    fnames["mathieu+bad_color_diffs+len_ttext"] = fnames["mathieu+bad_color_diffs"] + ["len_ttext"]
    return fnames[ftake]


def select_feature_keys(trees_features, ftake):
    log.warning("DEPRECATED")
    good_feature_keys = select_feature_keys_v2(ftake)
    if trees_features:
        fnames_all = _pick_all_features(trees_features)
        assert np.in1d(good_feature_keys, fnames_all).all()
    return good_feature_keys


def node_feats_to_numpy(node_features: Domfeature, feature_keys: List[str]):
    # Select subset from Domfeature, cast to numpy 1D array
    concat_ = []
    for feature_key in feature_keys:
        concat_.append(node_features[feature_key])  # type: ignore
    node_npfeatures = np.hstack(concat_)
    return node_npfeatures


def tree_features_to_npfeatures(tree_features: List[Domfeature], feature_keys: List[str]):
    tree_npfeatures_ = []
    tree_meta = []
    for node_id, node_features in enumerate(tree_features):
        node_npfeatures = node_feats_to_numpy(node_features, feature_keys)
        tree_npfeatures_.append(node_npfeatures)
        tree_meta.append(
            {"node_id": node_id, "xpath": node_features["_xpath"], "_flavour_id": node_features["_flavour_id"]}
        )
    tree_npfeatures = np.vstack(tree_npfeatures_)
    tree_metadf = pd.DataFrame(tree_meta)
    return tree_npfeatures, tree_metadf


def trees_features_to_npfeatures(trees_features: Dict[int, List[Domfeature]], feature_keys: List[str], num_workers=0):
    """
    Cast features into: array and DataFrame with metainformation
    """
    prepared_args = [(tree_features, feature_keys) for tree_features in trees_features.values()]
    results = vst.isave.Isaver_fast(
        None,
        prepared_args,
        tree_features_to_npfeatures,
        async_kind="process",
        num_workers=num_workers,
        progress="features_to_npfeatures",
    ).run()
    for row_id, (_, tree_metadf) in zip(trees_features.keys(), results):
        tree_metadf["row_id"] = row_id
    trees_npfeatures_, trees_metadfs_ = zip(*results)
    trees_npfeatures = np.vstack(trees_npfeatures_)
    trees_metadf = pd.concat(trees_metadfs_).reset_index(drop=True)
    return trees_npfeatures, trees_metadf


def remove_invisible_boxes0(tree_features: List[Domfeature], min_size=4) -> List[Domfeature]:
    invisibles = np.zeros(len(tree_features), dtype=bool)
    for node_id, node_features in enumerate(tree_features):
        w = node_features["w_orig"]
        h = node_features["h_orig"]
        invisibles[node_id] = w < min_size or h < min_size
    visible_tree_features = list(itertools.compress(tree_features, ~invisibles))
    return visible_tree_features


def remove_invisible_boxes(trees_features: Dict[int, List[Domfeature]], min_size=4) -> Dict[int, List[Domfeature]]:
    visible_trees_features = {}
    for row_id, tree_features in trees_features.items():
        visible_trees_features[row_id] = remove_invisible_boxes0(tree_features, min_size)
    return visible_trees_features
