import statistics
import logging
from enum import Enum
from io import StringIO

from eb_infex_worker.information_extraction.html_similarity import similarity
from lxml import html

from eb_infex_worker.information_extraction.pattern_detection.hashing import (
    compute_image_hash,
    compute_images_hashes_threaded,
)
from eb_infex_worker.information_extraction.pattern_detection.images_extraction import (
    are_images_identical,
    extract_images_from_page,
)
from eb_infex_worker.information_extraction.pattern_detection.utils import (
    image_extension_validator,
    prune_domain,
    stringify_tree_element,
    url_formatter,
    url_validator,
)

MIN_SIBLINGS_NB = 2  # minimum number of siblings for which we consider searching a pattern
MAX_SIBLINGS_TO_COMPARE = 5  # maximum number of siblings against which we compute the similarity
SIMILARITY_THRESHOLD = 0.2  # minimum value of the similarity for which we consider tw HTML subtrees to be similar


class TreeTraversalTask(str, Enum):
    SEARCH_PATTERN = "search_pattern"
    SEARCH_HREF = "search_href"


class PatternDetector:
    def __init__(self):

        self.tree = None
        self.page_url = None
        self.image_url = None
        self.s3_url = None
        self.html_document = None

    def __generate_xpath_from_node(self, node):
        try:
            image_xpath = self.tree.getpath(node)
            return image_xpath
        except Exception as ex:
            logging.warning(f"Exception on __generate_xpath_from_node :{ex}")
            image_xpath = "//{}".format(node.tag)
            for attrib_name, attrib_value in node.attrib.items():
                if attrib_name and attrib_value:
                    image_xpath += "[@{}='{}']".format(attrib_name, attrib_value)

            return image_xpath

    def __find_image_element_from_url(self):
        """Returns the DOM element containing the image of interest"""

        # Keep the part of the image URL that comes after the network location
        image_url_pruned = prune_domain(self.image_url)

        xpath_search_queries = [
            f"//img[contains(@src, '{image_url_pruned}')]",
            f"//img[contains(@srcset, '{image_url_pruned}')]",
            f"//img[contains(@*, '{image_url_pruned}')]",
            f"//*[contains(@src, '{image_url_pruned}')]",
            f"//a[contains(@href, '{image_url_pruned}')]",
            f"//*[contains(@style, '{image_url_pruned}')]",
        ]

        for query in xpath_search_queries:
            initial_nodes = self.tree.xpath(query)
            if initial_nodes:
                return initial_nodes[0]

        return None

    def __find_image_element_from_content(self):

        tuples = extract_images_from_page(self.tree, self.page_url)

        hashes_list = compute_images_hashes_threaded(tuples)
        if hashes_list:

            reference_hash = compute_image_hash(self.s3_url if self.s3_url else self.image_url)

            for image_xpath, image_hash in hashes_list:
                if are_images_identical(reference_hash, image_hash):
                    # Get element from XPath
                    node = self.tree.xpath(image_xpath)[0]

                    return node

        return None

    def __find_image_element(self):

        image_element = self.__find_image_element_from_url()

        if image_element is None:
            image_element = self.__find_image_element_from_content()

        return image_element

    def __find_family(self, node):
        """Returns the parent of node, node and a list of the other chidren of the ancestor of node"""

        parent = node.getparent()

        siblings = [child for child in parent.iterchildren() if child != node] if parent is not None else []

        return parent, node, siblings

    def __find_similarity(self, node, siblings):
        """Finds whether node has similar siblings. We compute the average similarity by analyzing the first siblings"""

        html_similarities = [
            similarity(stringify_tree_element(node), stringify_tree_element(sibling))
            for sibling in siblings[:MAX_SIBLINGS_TO_COMPARE]
        ]

        mean_similarity = statistics.mean(html_similarities)

        return mean_similarity > SIMILARITY_THRESHOLD

    def __find_referenced_urls(self, node):
        """Detects whether node contains references to other webpages

        Returns:
        ========
        str[]: if at least one reference is detected, returns the webpages referred to; else []
        """

        node_xpath = self.tree.getpath(node)

        xpath_search_queries = [
            f"{node_xpath}//a/@href",
            f"{node_xpath}/@href",
        ]

        links_found_set = set()
        for query in xpath_search_queries:
            for link in node.xpath(query):

                link = url_formatter(link, self.page_url)

                if url_validator(link) and link != self.page_url and not image_extension_validator(link):
                    links_found_set.add(link)

        links_found = list(links_found_set)

        return links_found

    def __traverse_tree_bottom_up(self, initial_node, end_node=None, task=TreeTraversalTask.SEARCH_PATTERN):
        """Traverse the tree up from an initial node and perform a check depending on the nature of task

        Parameters:
        ===========
        initial_node: HTML element
            the node from which we start
        end_node: HTML element
            the node after which we stop the traversal. If None, we stop the traversal at the root
        task: TreeTraversalTask
            the nature of the check to perform

        Returns:
        ========
        depends on the nature of the task
        """

        parent = initial_node
        depth = 0

        while parent is not None and parent != end_node:

            node = parent
            parent, node, siblings = self.__find_family(node)
            depth += 1

            if task == TreeTraversalTask.SEARCH_PATTERN:
                if len(siblings) >= MIN_SIBLINGS_NB:
                    if self.__pattern_validator(node, siblings):
                        return node

            elif task == TreeTraversalTask.SEARCH_HREF:
                hrefs = self.__find_referenced_urls(node)
                if hrefs:
                    hrefs_copy = hrefs.copy()
                    for href in hrefs:
                        # we remove hrefs that has the default value of javascript and does not contain a url
                        if href.endswith("javascript:"):
                            hrefs_copy.remove(href)
                    if len(hrefs_copy) > 0:
                        return hrefs_copy

        return None

    def __pattern_validator(self, node, siblings):
        """Returns whether the node and its siblings are similar and the node contains references to URLs"""

        return self.__find_similarity(node, siblings) and self.__find_referenced_urls(node)

    def search_pattern(self, html_document, page_url, image_url, s3_url=None):
        """Search whether the image image_url is part of a pattern in the HTML code html_document of the page page_url

        Parameters:
        ===========
        html_document: str
        page_url: str
        image_url: str
        s3_url: str
        Returns:
        ========
        bool
        """

        tree = html.parse(StringIO(html_document))

        self.tree = tree
        self.html_document = html_document
        self.page_url = page_url
        self.image_url = image_url
        self.s3_url = s3_url

        initial_node = self.__find_image_element()
        if initial_node is None:
            return False, None, None, None

        image_xpath = self.__generate_xpath_from_node(initial_node)

        # Detect whether there is a pattern among the siblings of the ancestors of the initial node
        final_node = self.__traverse_tree_bottom_up(initial_node)
        initial_node.attrib["data-nv-flavour"] = "image"

        if final_node is not None:
            # Detect whether there are some href in <a> tags in the pattern piece where the initial node is
            hrefs = self.__traverse_tree_bottom_up(
                initial_node, end_node=final_node.getparent(), task=TreeTraversalTask.SEARCH_HREF
            )

            if hrefs:
                return True, image_xpath, final_node, hrefs

        return False, image_xpath, final_node, None


if __name__ == "__main__":

    html_doc_path = "html/html.html"

    with open(html_doc_path, "r") as f:
        html_doc = f.read()

    page_url = "http://www.laptitedum.fr/survetement-fendi-femme-c-110_117.html"
    image_url = "http://www.laptitedum.fr/bmz_cache/e/Survetement%20Capuche%20Fendi%20Femme%202020%20Ensemble%20Jogging%20Fendi%20Bag%20Bugs%20Femme%20FFF011.image.400x313.jpg"  # noqa:E501

    patternDetector = PatternDetector()

    patternDetector.search_pattern(html_doc, page_url, image_url)
