import logging
import math
import re
import statistics
from copy import deepcopy
from statistics import mean

import numpy as np
import regex

log = logging.getLogger(__name__)

FLAVOURS = ["normal", "title", "price", "image"]

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
    "usd",
    "USD",
]


def get_h_title_value(tag_name):
    for i in range(1, 7):
        if tag_name == "h{}".format(i):
            return 1 - (i - 1) * 0.17

    return 0


def or_regex(symbols):
    """Return a regex which matches any of ``symbols``"""
    return re.compile("|".join(re.escape(s) for s in symbols))


def is_currency_visible(text):
    if len(regex.findall(r"\p{Sc}", text)) > 0:
        return True
    elif or_regex(SAFE_CURRENCY_SYMBOLS).search(text):
        return True

    return False


def get_lxml_depth(node):
    d = 0
    while node is not None:
        d += 1
        node = node.getparent()
    return d


def get_lxml_inversed_depth(node, depth=0, min_concat=True):
    children = node.getchildren()
    if not children:
        return depth
    else:
        if min_concat:
            return min([get_lxml_inversed_depth(c, depth=depth + 1, min_concat=min_concat) for c in children])
        else:
            return max([get_lxml_inversed_depth(c, depth=depth + 1, min_concat=min_concat) for c in children])


def get_distance_between_2_nodes(node_1, node_2):
    dist = 0
    list_node_1 = [node_1]
    list_node_2 = [node_2]

    while len(list(set(list_node_1) & set(list_node_2))) == 0:
        if node_1 is not None:
            node_1 = node_1.getparent()
            list_node_1.append(node_1)

        if node_2 is not None:
            node_2 = node_2.getparent()
            list_node_2.append(node_2)

        dist += 1

    return dist


def get_ratio_digits_characters(text):
    len_text_without_whitespace = len("".join(text.split()))
    nb_digits = sum(c.isdigit() for c in text)

    if not len_text_without_whitespace:
        return 0

    return nb_digits / len_text_without_whitespace


def get_capital_percentage_node(node, text):
    if node.get("data-nv-style-texttransform") == "uppercase":
        capitals_percentage = 1.0
    else:
        capitals_percentage = [char.isupper() for char in text if char.isalpha()]
        capitals_percentage = mean(capitals_percentage) if len(capitals_percentage) > 0 else 0
    return capitals_percentage


def get_parent_tags(node):
    # first get merge node tags
    tags = node.get("data-nv-mergednodetags", "").split(" ")
    tags = [t.lower() for t in tags]

    # get parent tree tags
    while node is not None:
        tags.append(node.tag.lower())
        node = node.getparent()
    return tags


def feat_compute_distance(image_x, image_y, x, y, image_w, image_h, w, h, page_width, page_height):
    BAD = (np.c_[image_x, image_y, x, y] < 0).any()
    BAD |= (np.c_[image_x, image_y, x, y] > np.tile([page_width, page_height], 2)).any()
    BAD |= (np.c_[image_w, image_h, w, h] < 1).any()
    if BAD:
        dist = 150
    else:
        x_dist = (
            0
            if (image_x <= x <= image_x + image_w or x <= image_x <= x + w)
            else min(abs(x + w - image_x), abs(image_x + image_w - x))
        )
        y_dist = (
            0
            if (image_y <= y <= image_y + image_h or y <= image_y <= y + h)
            else min(abs(y + h - image_y), abs(image_y + image_h - y))
        )
        dist = math.sqrt((x_dist ** 2) + (y_dist ** 2))
    return dist


def convert_lxml_tree_to_features_price(tree, row_id):
    tree_features = []
    tree_insights = []

    image_node = tree.xpath("//*[@data-nv-flavour='image']")[0]

    image_x = float(image_node.get("data-nv-x", 0))
    image_y = float(image_node.get("data-nv-y", 0))
    image_w = float(image_node.get("data-nv-w", 0))
    image_h = float(image_node.get("data-nv-h", 0))

    heights = [100]
    widths = [100]
    for node in tree.xpath(".//*"):
        widths.append(float(node.get("data-nv-w", 0)))
        heights.append(float(node.get("data-nv-h", 0)))
    page_width = max(widths)
    page_height = max(heights)

    for node in tree.xpath(".//*"):
        feats = {}
        feats["row_id"] = row_id
        if node.get("data-nv-flavour"):
            feats["flavour_id"] = FLAVOURS.index(node.get("data-nv-flavour"))
        else:
            feats["flavour_id"] = 0

        feats["imnode_distance"] = get_distance_between_2_nodes(node, image_node)

        node_text = " ".join(node.text.strip().split()) if node.text else ""
        node_text_content = " ".join(node.text_content().strip().split())

        # if the text content (raw_price) is longer than 50 character we do not consider it as a potential candidate.
        if len(node_text_content) < 50:
            feats["currency_detected"] = is_currency_visible(node_text_content)
            # feats['len_text'] = len(node_text)
            feats["len_tcontent"] = len(node_text_content)
            feats["ratio_digits_characters"] = get_ratio_digits_characters(node_text_content)

            tag = node.tag.lower()
            feats["tags_present"] = np.isin(MOST_PRESENT_TAGS, tag)
            feats["h_title_value"] = get_h_title_value(tag)
            feats["flow_tag"] = tag in FLOW_CONTENT_TAGS
            feats["phrasing_tag"] = tag in PHRASING_CONTENT_TAGS
            feats["palpable_tag"] = tag in PALPABLE_CONTENT_TAGS

            parent_tags = get_parent_tags(node)
            feats["line_through"] = (
                tag == "del" or "del" in parent_tags or node.get("data-nv-style-textdecorationline") == "line-through"
            )

            attributes_text = " ".join(
                [
                    v
                    for k, v in node.attrib.items()
                    if (not k.startswith("data-nv-")) and (k not in ["src", "href", "bomtype"])
                ]
            ).lower()
            feats["price_in_attributes"] = "price" in attributes_text

            x = float(node.get("data-nv-x", 0))
            y = float(node.get("data-nv-y", 0))
            w = float(node.get("data-nv-w", 0))
            h = float(node.get("data-nv-h", 0))

            dist = feat_compute_distance(image_x, image_y, x, y, image_w, image_h, w, h, page_width, page_height)

            feats["image_dist"] = int(dist)
            feats["x"] = x / page_width
            feats["y"] = y / page_height
            feats["w"] = w / page_width
            feats["h"] = h / page_height

            feats["visible"] = node.get("data-nv-visible") == "true"

            tree_features.append(feats)

            insights = deepcopy(feats)
            insights["node_text"] = node_text
            insights["node_text_content"] = node_text_content
            insights["attributes_text"] = attributes_text
            insights["tag"] = node.tag

            insights["x"] = x
            insights["y"] = y
            insights["w"] = w
            insights["h"] = h
            insights["image_x"] = image_x
            insights["image_y"] = image_y
            insights["image_w"] = image_w
            insights["image_h"] = image_h
            insights["page_width"] = page_width
            insights["page_height"] = page_height

            tree_insights.append(insights)

    return tree_features, tree_insights


def convert_lxml_tree_to_features_title(tree, row_id):
    tree_features = []
    tree_insights = []

    image_node = tree.xpath("//*[@data-nv-flavour='image']")
    if not image_node:
        image_node = tree.xpath("//*")
    image_node = image_node[0]

    image_x = float(image_node.get("data-nv-x", 0))
    image_y = float(image_node.get("data-nv-y", 0))
    image_w = float(image_node.get("data-nv-w", 0))
    image_h = float(image_node.get("data-nv-h", 0))

    heights = [100]
    widths = [100]
    font_sizes = []
    for node in tree.xpath(".//*"):
        widths.append(float(node.get("data-nv-w", 0)))
        heights.append(float(node.get("data-nv-h", 0)))
        if "px" in node.get("data-nv-style-fontsize", ""):
            node_text = " ".join(node.text.strip().split()) if node.text else ""
            font_sizes.extend([float(node.get("data-nv-style-fontsize", "").replace("px", ""))] * len(node_text))
    page_width = max(widths)
    page_height = max(heights)

    font_sizes = [f for f in font_sizes if f > 0]
    if font_sizes:
        median_font_size = statistics.median(font_sizes)
    else:
        median_font_size = 12

    for node in tree.xpath(".//*"):
        feats = {}
        feats["row_id"] = row_id
        if node.get("data-nv-flavour"):
            feats["flavour_id"] = FLAVOURS.index(node.get("data-nv-flavour"))
        else:
            feats["flavour_id"] = 0

        if "px" in node.get("data-nv-style-fontsize", ""):
            feats["fontsize"] = float(node.get("data-nv-style-fontsize", "").replace("px", "")) / median_font_size
        else:
            feats["fontsize"] = 1.0

        feats["imnode_distance"] = get_distance_between_2_nodes(node, image_node)

        feats["inversed_depth"] = get_lxml_inversed_depth(node, min_concat=False)
        feats["depth"] = get_lxml_depth(node)

        node_text = " ".join(node.text.strip().split()) if node.text else ""
        node_text_content = " ".join(node.text_content().strip().split())
        # feats['len_text'] = len(node_text)
        feats["len_tcontent"] = len(node_text_content)
        # feats['ratio_digits_characters'] = get_ratio_digits_characters(node_text_content)

        feats["capital_percentage"] = get_capital_percentage_node(node=node, text=node_text_content)

        tag = node.tag.lower()
        feats["tags_present"] = np.isin(MOST_PRESENT_TAGS, tag)
        feats["h_title_value"] = get_h_title_value(tag)
        # feats['image_tag'] = tag in FRAME_IMAGES_AND_AUDIO_TAGS
        # feats['list_table_form_tag'] = tag in LIST_TAGS + TABLE_TAGS + FORMS_AND_INPUT_TAGS
        feats["flow_tag"] = tag in FLOW_CONTENT_TAGS
        feats["phrasing_tag"] = tag in PHRASING_CONTENT_TAGS
        feats["palpable_tag"] = tag in PALPABLE_CONTENT_TAGS

        attributes_text = " ".join(
            [
                v
                for k, v in node.attrib.items()
                if (not k.startswith("data-nv-")) and (k not in ["src", "href", "bomtype"])
            ]
        ).lower()
        feats["name_in_attributes"] = "name" in attributes_text
        feats["title_in_attributes"] = "title" in attributes_text

        x = float(node.get("data-nv-x", 0))
        y = float(node.get("data-nv-y", 0))
        w = float(node.get("data-nv-w", 0))
        h = float(node.get("data-nv-h", 0))

        dist = feat_compute_distance(image_x, image_y, x, y, image_w, image_h, w, h, page_width, page_height)

        feats["image_dist"] = int(dist)
        feats["x"] = x / page_width
        feats["y"] = y / page_height

        feats["visible"] = node.get("data-nv-visible") == "true"

        tree_features.append(feats)

        insights = deepcopy(feats)
        insights["node_text"] = node_text
        insights["node_text_content"] = node_text_content
        insights["attributes_text"] = attributes_text
        insights["tag"] = tag
        insights["mergednodetags"] = node.get("data-nv-mergednodetags", "").split(" ")

        tree_insights.append(insights)

    return tree_features, tree_insights
