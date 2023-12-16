import logging
from timeit import default_timer as timer

import lxml.html
import numpy as np
import networkx as nx
import selenium
import selenium.webdriver
from selenium.webdriver.common.by import By

log = logging.getLogger(__name__)


def tree_remove_nodes(tree, kill_check):
    """
    Kill nodes in networkx tree if they satisfy kill_check(node, node_data)
    """
    tree = tree.copy()
    repeat = True
    while repeat:
        node_names = list(tree.nodes)
        for node in node_names:
            node_data = tree.nodes.data()[node]
            if kill_check(node, node_data):
                parents = list(tree.predecessors(node))
                if len(parents) == 0:
                    tree.remove_node(node)
                elif len(parents) == 1:
                    parent = parents[0]
                    for succ in tree.successors(node):
                        tree.add_edge(parent, succ)
                    tree.remove_node(node)
                elif len(parents) > 1:
                    raise RuntimeError("Parents > 1, not a tree")
        # If previous step removed nodes - run again
        repeat = len(tree) < len(node_names)
    return tree


def lxml_tree_add_children(T, lxml_tree, lxml_node):
    """
    Recursively read lxml tree, add nodes to networkx tree "T"
    """
    node_xpath = lxml_tree.getpath(lxml_node)
    T.add_node(node_xpath, xpath=node_xpath)
    for lxml_child in lxml_node.iterchildren():
        child_xpath = lxml_tree.getpath(lxml_child)
        T.add_node(child_xpath, xpath=child_xpath)
        T.add_edge(node_xpath, child_xpath)
        lxml_tree_add_children(T, lxml_tree, lxml_child)


def pagepath_to_nxtree_via_lxml(pagepath):
    """
    Load nxtree from pagepath via lxml parser
    """
    try:
        with pagepath.open("r") as f:
            lxml_tree = lxml.html.parse(f)
    except Exception as ex:
        log.debug(f"Graph loading encountered exception: {ex}")
        return None

    # Create nx tree recusively
    tree = nx.DiGraph()
    lxml_root = lxml_tree.getroot()
    lxml_tree_add_children(tree, lxml_tree, lxml_root)

    # Kill all comment nodes and those we can't query via xpath
    def comment_or_bad_xpath_check(node, ndata):
        try:
            lxml_node = lxml_tree.xpath(ndata["xpath"])[0]
            if isinstance(lxml_node, lxml.html.HtmlComment):
                return True
        except lxml.etree.XPathEvalError:
            return True
        return False

    tree = tree_remove_nodes(tree, comment_or_bad_xpath_check)
    return tree


def refine_xpath_lxml(tree, xpath):
    # Make sure xpath can be retrieved from lxml_tree
    if not isinstance(xpath, str):
        return None
    refined = None
    try:
        element = tree.xpath(xpath)[0]
    except IndexError:
        log.debug(f"Could not read xpath {xpath}")
        return None
    refined = tree.getpath(element)
    assert tree.xpath(refined)[0] == element
    return refined


def refine_xpath_selenium(driver, xpath):
    # Make sure xpath can be retrieved via selenium
    if not isinstance(xpath, str):
        return None
    try:
        driver.find_element(By.XPATH, xpath)
        return xpath
    except selenium.common.exceptions.WebDriverException:
        return None


def driver_init_firefox(headless=True, timeout=5):
    # https://stackoverflow.com/questions/17533024/how-to-set-selenium-python-webdriver-default-timeout
    profile = selenium.webdriver.FirefoxProfile()
    profile.set_preference("http.response.timeout", timeout)
    profile.set_preference("dom.max_script_run_time", timeout)
    options = selenium.webdriver.FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    driver = selenium.webdriver.Firefox(firefox_options=options, firefox_profile=profile)
    driver.set_page_load_timeout(timeout)
    driver.implicitly_wait(timeout)
    return driver


def assign_fake_selenium_meta(graph):
    for node, ndata in graph.nodes.data():
        smeta = {"ltrd": np.ones(4) * np.nan, "is_displayed": False, "reachable": False}
        graph.nodes[node]["smeta"] = smeta


def assign_selenium_meta(driver, graph, bfs_root, page_timeout, total_timeout):
    """
    Starting from bfs_root iterate graph, adding selenium meta
        - Stop when total_timeout exceeded
    """
    # Now populate with selenium stuff
    start_time = timer()
    driver.set_page_load_timeout(page_timeout)
    driver.implicitly_wait(page_timeout)
    bfs_tree = nx.bfs_tree(graph.to_undirected(), bfs_root)
    enriched = 0
    for node in bfs_tree.nodes():
        xpath = graph.nodes[node]["xpath"]
        if (timer() - start_time) > total_timeout:
            log.info(f"Selenium enrichment longer than {total_timeout}s." f" Breaking after {enriched} nodes enriched.")
            break
        try:
            element = driver.find_element(By.XPATH, xpath)
            is_displayed = element.is_displayed()
            if is_displayed:
                r = element.rect
                ltrd = np.r_[r["x"], r["y"], r["x"] + r["width"], r["y"] + r["height"]]
                graph.nodes[node]["smeta"]["ltrd"] = ltrd
            graph.nodes[node]["smeta"]["is_displayed"] = is_displayed
            graph.nodes[node]["smeta"]["reachable"] = True
            enriched += 1
        except selenium.common.exceptions.WebDriverException:
            pass


def none2str(x):
    return "" if x is None else x


def enrich_tree_with_lxml_meta(lxml_tree, tree):
    for node, ndata in tree.nodes.data():
        xnode = lxml_tree.xpath(ndata["xpath"])[0]
        xnode_params = dict(xnode.items())
        lmeta = {
            "tag": xnode.tag,
            "text": none2str(xnode.text),
            "text_content": xnode.text_content(),
            "class": none2str(xnode_params.get("class")),
            "id": none2str(xnode_params.get("id")),
        }
        tree.nodes[node]["lmeta"] = lmeta
