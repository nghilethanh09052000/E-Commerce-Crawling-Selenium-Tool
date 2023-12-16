import copy
import re
import logging
from typing import List

import numpy as np
import pandas as pd
import networkx as nx
import lxml.html
import lxml.etree

import eb_infex_worker.information_extraction.vst as vst


from eb_infex_worker.information_extraction.dom.misc import (
    textclean,
    get_color_rgba,
    remove_control_chars,
    check_flavour_presence,
)
from eb_infex_worker.information_extraction.utils.snippets import Failure

log = logging.getLogger(__name__)


# Create trees


def lxml_from_string(tree_string):
    lxml_root = lxml.html.fromstring(tree_string)
    lxml_rtree = lxml_root.getroottree()
    assert lxml_root is lxml_rtree.getroot()
    return lxml_root, lxml_rtree


def _lxml_tree_add_children_v2(T, lxml_rtree, lxml_node):
    """
    Recursively read lxml tree, add nodes to networkx tree "T", keep references
    to original lxml nodes

    - The resulting tree is not picklable
    """
    node_xpath = lxml_rtree.getpath(lxml_node)
    T.add_node(node_xpath, xpath=node_xpath, lxml_node=lxml_node)
    for lxml_child in lxml_node.iterchildren():
        child_xpath = lxml_rtree.getpath(lxml_child)
        T.add_node(child_xpath, xpath=child_xpath, lxml_node=lxml_node)
        T.add_edge(node_xpath, child_xpath)
        _lxml_tree_add_children_v2(T, lxml_rtree, lxml_child)


def lxml_to_nx(lxml_root, lxml_rtree):
    """Create unpicklable networx tree from LXML tree"""
    nx_tree = nx.DiGraph()
    _lxml_tree_add_children_v2(nx_tree, lxml_rtree, lxml_root)
    return nx_tree


def create_annotated_nx_tree(tree_string):
    # Create networkx graph
    lxml_root, lxml_rtree = lxml_from_string(tree_string)
    xpath_root = lxml_rtree.getpath(lxml_root)
    nx_tree = lxml_to_nx(lxml_root, lxml_rtree)
    # Assign tree depth, height, flavours
    node_depths = dict(nx.shortest_path_length(nx_tree, xpath_root))
    for node, ndata in nx_tree.nodes.data():
        ndata["flavour"] = ndata["lxml_node"].get("data-nv-flavour", "normal")
        ndata["depth"] = node_depths[node]
        ndata["height"] = 0
    bfs_preds = list(nx.bfs_predecessors(nx_tree, xpath_root))[::-1]
    for x, y in bfs_preds:
        nx_tree.nodes[y]["height"] = max(nx_tree.nodes[y]["height"], nx_tree.nodes[x]["height"] + 1)
    return nx_tree, lxml_root, lxml_rtree


# Merge nodes


def _nx_tree_parent_child_merge(
    original_nx_tree: nx.DiGraph, leafs_only: bool, empty_child_only: bool, guard_flavours: bool
):
    """
    For NX tree: Merge single parents with their single children
      - Create a copy of the nx tree
      - Record pointers to the original NX tree
      - Repeatedly merge nodes together by updating the pointers
      - In this way we avoid the task of merging attributes

    Args:
        leafs_only: only merge the leaf nodes
        empty_child_only: only merge children with no text
        guard_flavours: prevent two flavoured nodes from being merged
    """
    nx_tree = original_nx_tree.copy()
    # Initialize helper node properties
    for node, ndata in nx_tree.nodes.data():
        ndata["original_nodes"] = [node]
        ndata["flavour"] = ndata["lxml_node"].get("data-nv-flavour", "normal")
        assert ndata["flavour"] is not None
    # Repeatedly merge leaf nodes into single-child parents
    repeat = True
    while repeat:
        repeat = False
        for node, ndata in list(nx_tree.nodes.data()):
            degree = nx_tree.degree(node)
            # Check for leaf nodes
            if leafs_only:
                if degree != 1:
                    continue
            # Check for parent with single child
            parents = list(nx_tree.predecessors(node))
            if not len(parents):
                continue
            parent = parents[0]
            if nx_tree.out_degree(parent) != 1:
                continue
            # Check for empty child
            if empty_child_only:
                text = textclean(nx_tree.nodes[node]["lxml_node"].text)
                if len(text) == 0:
                    continue
            # Merged flavour - overwrite normal
            if nx_tree.nodes[parent]["flavour"] == "normal":
                nx_tree.nodes[parent]["flavour"] = ndata["flavour"]
            else:
                if ndata["flavour"] != "normal":
                    # If abnormal parent and child, and guarding - stop merging
                    if guard_flavours:
                        continue
                    else:
                        log.info(
                            "Flavor overwritten {} <- {}".format(nx_tree.nodes[parent]["flavour"], ndata["flavour"])
                        )
                        nx_tree.nodes[parent]["flavour"] = ndata["flavour"]
            nx_tree.nodes[parent]["original_nodes"].extend(ndata["original_nodes"])
            if degree == 1:
                nx_tree.remove_node(node)
            else:
                nx_tree = nx.contracted_edge(nx_tree, (parent, node))
            repeat = True
    return nx_tree


def _bool_jspy(value):
    return value == "true"


def _bool_pyjs(value):
    return "true" if value else "false"


def _attr_merge_bool_any(values):
    return _bool_pyjs(any([_bool_jspy(x) for x in values]))


def _attr_merge_most_freq(values):
    freqdict = {}
    for value in values:
        freqdict[value] = freqdict.get(value, 0) + 1
    most_freq, _ = sorted(freqdict.items(), key=lambda x: x[1])[-1]
    return most_freq


def _nx_tree_remove_comment_nodes(original_nx_tree):
    nx_tree = original_nx_tree.copy()
    for node, ndata in list(nx_tree.nodes.data()):
        if isinstance(ndata["lxml_node"], lxml.html.HtmlComment):
            nx_tree.remove_node(node)
    return nx_tree


def lxml_tree_parent_child_merge(
    lxml_root,
    lxml_rtree,
    attribute_merge_strategy="last_child",
    leafs_only=True,
    empty_child_only=False,
    guard_flavours=True,
):
    """
    For LXML tree: Merge parents with their single childen

    Steps:
        1) Create NX tree representation
        2) Merge parents/children there (simply keep a list of merged nodes)
        3) Recreate LXML tree from NX tree, this time merging attributes
    """
    original_nx_tree = lxml_to_nx(lxml_root, lxml_rtree)
    nx_tree = _nx_tree_remove_comment_nodes(original_nx_tree)
    nx_tree = _nx_tree_parent_child_merge(nx_tree, leafs_only, empty_child_only, guard_flavours)
    if len(nx_tree) == len(original_nx_tree):
        return lxml_root, lxml_rtree

    # Recompute features if graph changed
    for node, ndata in nx_tree.nodes.data():
        # Retrieve original lxml nodes
        orig_lxml_nodes = []
        for node_name in ndata["original_nodes"]:
            node = original_nx_tree.nodes[node_name]
            orig_lxml_nodes.append(node["lxml_node"])
        # Create new node (copying the original)
        old_lxml_node = orig_lxml_nodes[0]
        new_lxml_node = copy.deepcopy(old_lxml_node)
        for child in new_lxml_node.getchildren():
            new_lxml_node.remove(child)
        # Assign flavour: nx -> lxml node
        if len(ndata["original_nodes"]) > 1:
            # text: Union of node texts
            texts = [n.text for n in orig_lxml_nodes if n.text]
            new_lxml_node.text = " ".join(texts)
            # Collect all attributes
            all_old_attribs = {}
            for old_node in orig_lxml_nodes:
                for k, v in old_node.attrib.items():
                    all_old_attribs.setdefault(k, []).append(v)
            # Merge attributes
            if attribute_merge_strategy == "last_child":
                # (Follow Mat's js) data-nv attributes - assign last child's
                for k, values in all_old_attribs.items():
                    if k.startswith("data-nv"):
                        merged_value = values[-1]
                    else:
                        merged_value = " ".join(v)
                    all_old_attribs[k] = merged_value
            elif attribute_merge_strategy == "heuristic":
                xy_attr_names = ["data-nv-x", "data-nv-y", "data-nv-w", "data-nv-h"]
                xy_attrs = [[float(x) for x in all_old_attribs.get(k, [0])] for k in xy_attr_names]
                xywhs = np.vstack(xy_attrs).T.astype(int)
                # Cast to left, top, right, down
                ltrds = xywhs.copy()
                ltrds[:, 2:] += ltrds[:, :2]
                # Create single ltrds/xywh (biggest surrounding area)
                ltrd = np.r_[ltrds[:, :2].min(axis=0), ltrds[:, 2:].max(axis=0)]
                xywh = ltrd.copy()
                xywh[2:] -= xywh[:2]
                # Assign
                xy_attrs = {}
                for key, value in zip(xy_attr_names, xywh):
                    xy_attrs[key] = str(value)
                for k, values in all_old_attribs.items():
                    if k.startswith("data-nv"):
                        if k in xy_attrs:
                            merged_value = xy_attrs[k]
                        elif k == "data-nv-reachable":
                            # Not used anywhere
                            merged_value = _attr_merge_bool_any(values)
                        elif k == "data-nv-visible":
                            merged_value = _attr_merge_bool_any(values)
                        elif k in ["data-nv-css-backgroundcolor", "data-nv-css-color"]:
                            avg_color = np.vstack([get_color_rgba(x) for x in values]).mean(axis=0).astype(int)
                            merged_value = "rgba(" + ", ".join(avg_color.astype(str).tolist()) + ")"
                        elif k == "data-nv-css-display":
                            merged_value = _attr_merge_most_freq(values)
                        elif k == "data-nv-css-fontfamily":
                            merged_value = _attr_merge_most_freq(values)
                        elif k == "data-nv-css-fontsize":
                            avg_size = int(
                                np.mean([float(re.match(r"([\d\.]+)px", x).group(1)) for x in values]).round()
                            )
                            merged_value = f"{avg_size}px"
                        elif k == "data-nv-css-fontstyle":
                            merged_value = _attr_merge_most_freq(values)
                        elif k == "data-nv-css-fontweight":
                            # Not used anywhere
                            avg_weight = int(np.mean([int(x) for x in values]).round())
                            merged_value = str(avg_weight)
                        elif k == "data-nv-css-justifycontent":
                            # Not used anywhere
                            merged_value = _attr_merge_most_freq(values)
                        elif k == "data-nv-css-textalign":
                            # Not used anywhere
                            merged_value = _attr_merge_most_freq(values)
                        elif k == "data-nv-css-textdecorationline":
                            if "line-through" in values:
                                merged_value = "line-through"
                            else:
                                merged_value = "none"
                        elif k == "data-nv-css-texttransform":
                            if "uppercase" in values:
                                merged_value = "uppercase"
                            else:
                                merged_value = "none"
                        elif k == "data-nv-flavour":
                            # flavour will be reassigned later anyway
                            merged_value = values[-1]
                        else:
                            raise NotImplementedError()
                    else:
                        merged_value = " ".join(v)
                    all_old_attribs[k] = merged_value
            else:
                raise RuntimeError()
            # Assign new attributes, ensure XML compatability
            for k, v in all_old_attribs.items():
                new_lxml_node.attrib[k] = remove_control_chars(v)
        new_lxml_node.attrib["data-nv-flavour"] = ndata["flavour"]
        ndata["lxml_node"] = new_lxml_node

    # Create new lxml tree
    xpath_root_image = lxml_rtree.getpath(lxml_root)
    bfs_succ = list(nx.bfs_successors(nx_tree, xpath_root_image))
    for parent, childen in bfs_succ:
        lxml_node_parent = nx_tree.nodes[parent]["lxml_node"]
        for child in childen:
            lxml_node_child = nx_tree.nodes[child]["lxml_node"]
            lxml_node_parent.append(lxml_node_child)

    new_lxml_root = nx_tree.nodes[xpath_root_image]["lxml_node"]
    new_lxml_rtree = new_lxml_root.getroottree()
    return new_lxml_root, new_lxml_rtree


def lxml_tree_parent_child_merge_with_checks(
    tree_string,
    df_metarow,
    flavours: List[str],
    attribute_merge_strategy: str,
    leafs_only: bool,
    empty_child_only: bool,
    guard_flavours: bool,
):
    """
    For LXML tree, merge parents/children, do metadata checks

    Checks:
      - Does number of initial nodes correspond
      - Are the same flavours present after merging
    """

    def fail(error_string):
        log.info("Error at df_metarow {}\n{}".format(df_metarow, error_string))
        return Failure(error_string)

    lxml_root, lxml_rtree = lxml_from_string(tree_string)

    # Check: num initial nodes
    n_nodes = len(lxml_rtree.xpath(".//*"))
    if df_metarow["n_after"] != n_nodes:
        return fail(f"Initial node number changed {df_metarow['n_after']} -> {n_nodes}")

    lxml_root, lxml_rtree = lxml_tree_parent_child_merge(
        lxml_root, lxml_rtree, attribute_merge_strategy, leafs_only, empty_child_only, guard_flavours
    )

    # Check presence of all previously flavoured nodes
    fl_before_merge = df_metarow.loc[flavours].to_dict()
    fl_after_merge = check_flavour_presence(lxml_rtree, flavours)
    change = pd.DataFrame.from_dict({"before": fl_before_merge, "after": fl_after_merge}, orient="index")
    if fl_before_merge != fl_after_merge:
        return fail("Flavour presence changed after merge:\n{}".format(change))

    # Count new node number, convert to picklable string
    nnodes_after_merge = len(lxml_rtree.xpath(".//*"))
    tree_string = lxml.etree.tostring(lxml_root, encoding="UTF-8", pretty_print=True)
    return tree_string, nnodes_after_merge


def load_tree_pkg(path_tree):
    """
    Load tree_pkg, merge into single DataFrame

    tree_pkg: defined in experiments.preprocess_pages.convert_pages_to_lxml
    """
    tree_pkg = vst.load_pkl(path_tree)
    df_pages = tree_pkg["df_pages"]
    df_metas = tree_pkg["df_metas"]
    tree_strings = tree_pkg["tree_strings"]
    # Join all pandas data
    df_domtrees = df_metas.drop(columns="split").join(df_pages).join(tree_strings.rename("tree_string"))
    nflavours = ["normal"] + tree_pkg["flavours"]
    return df_domtrees, tree_pkg["window_size"], nflavours
