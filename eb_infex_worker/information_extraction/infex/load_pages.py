import logging
from pathlib import Path

import numpy as np
import pandas as pd

from eb_infex_worker.information_extraction.infex.nxtools import tree_remove_nodes

log = logging.getLogger(__name__)


def load_moderation_excel_file(table_path, folder) -> pd.DataFrame:
    folder = Path(folder)
    df_pages = pd.read_excel(table_path, engine="openpyxl")
    # / Cleanup dataframe
    df_pages = df_pages.drop([])  # Bad examples
    df_pages = df_pages[~df_pages.file_name.isna()]  # title must be present
    # df_pages = df_pages[~df_pages.post_price_path.isna()]  # price must be present
    # df_pages = df_pages[~df_pages.post_image_path.isna()]  # image must be present

    # Put path to save page
    df_pages = df_pages.assign(pagepath=df_pages.file_name.apply(lambda x: folder / x))
    return df_pages


def add_depth_and_flavour_to_nxtree(tree, xpaths):
    tree = tree.copy()
    flavour_map = {v: k for k, v in xpaths.items()}
    for node, ndata in tree.nodes.data():
        node_xpath = ndata["xpath"]
        tree.nodes[node]["flavour"] = flavour_map.get(node_xpath, "normal")
        tree.nodes[node]["depth"] = node_xpath.count("/")
    return tree


def delete_invisible_and_unreachable_nodes(graph, keep_flavours=True):
    # Kill all invisible or unreachable nodes
    def node_check(node, ndata):
        visible = ndata["smeta"]["is_displayed"]
        reachable = ndata["smeta"]["reachable"]
        KILL = not visible or not reachable
        if keep_flavours and (ndata["flavour"] != "normal"):
            KILL = False
        return KILL

    return tree_remove_nodes(graph, node_check)


def merge_onechild_nodes(original_graph, guard_flavours=True):
    """
    Repeatedly merge parents with single childen
    """
    graph = original_graph.copy()
    # xpaths -> pointers to original graph
    for node, ndata in graph.nodes.data():
        ndata["onodes"] = [node]
    # Repeatedly merge leaf nodes into single-child parents
    repeat = True
    while repeat:
        repeat = False
        for node, ndata in list(graph.nodes.data()):
            degree = graph.degree(node)
            if degree != 1:
                continue
            parents = list(graph.predecessors(node))
            if not len(parents):
                continue
            parent = parents[0]
            if graph.out_degree(parent) != 1:
                continue
            # Merged flavour - overwrite normal
            if graph.nodes[parent]["flavour"] == "normal":
                graph.nodes[parent]["flavour"] = ndata["flavour"]
            else:
                if ndata["flavour"] != "normal":
                    # If abnormal parent and child, and guarding - stop merging
                    if guard_flavours:
                        continue
                    else:
                        log.info("Flavor overwritten {} <- {}".format(graph.nodes[parent]["flavour"], ndata["flavour"]))
                        graph.nodes[parent]["flavour"] = ndata["flavour"]

            graph.nodes[parent]["onodes"].extend(ndata["onodes"])
            graph.remove_node(node)
            repeat = True
    if len(graph) == len(original_graph):
        return graph
    # Recompute features if graph changed
    for node, ndata in graph.nodes.data():
        if len(ndata["onodes"]) == 1:
            continue

        def get_originals(key1, key2):
            originals = []
            for onode in ndata["onodes"]:
                originals.append(original_graph.nodes.data()[onode][key1][key2])
            return originals

        # / Update smeta
        # Figuring out ltrd box
        ltrds = np.vstack(get_originals("smeta", "ltrd"))
        if np.isnan(ltrds).any():
            ltrds = ltrds[
                ~np.isnan(ltrds).any(1),
            ]
        if len(ltrds):
            ltrd = np.r_[ltrds[:, :2].min(0), ltrds[:, 2:].max(0)]
        else:
            ltrd = np.ones(4) * np.nan
        is_displayed = any(get_originals("smeta", "is_displayed"))
        reachable = any(get_originals("smeta", "reachable"))
        graph.nodes[node]["smeta"]["ltrd"] = ltrd
        graph.nodes[node]["smeta"]["is_displayed"] = is_displayed
        graph.nodes[node]["smeta"]["reachable"] = reachable
        # / Update lmeta
        tags = get_originals("lmeta", "tag")
        texts = get_originals("lmeta", "text")
        text_contents = get_originals("lmeta", "text_content")
        classes = get_originals("lmeta", "class")
        ids = get_originals("lmeta", "id")
        graph.nodes[node]["lmeta"]["tag"] = ",".join(tags)
        graph.nodes[node]["lmeta"]["text"] = ",".join(texts)
        graph.nodes[node]["lmeta"]["text_content"] = text_contents[0]
        graph.nodes[node]["lmeta"]["class"] = ",".join(classes)
        graph.nodes[node]["lmeta"]["id"] = ",".join(ids)
    return graph
