from eb_infex_worker.information_extraction.pattern_detection.utils import (
    image_extension_validator,
    url_formatter,
    url_validator,
)


def extract_images_from_page(tree, page_url):

    # Retrieve content of all src values in <img> tags
    image_elements = tree.xpath("//img/@src")

    # Retrieve content of all href values in <a> tags (those may be images in fact)
    href_elements = tree.xpath("//a/@href")

    image_elements.extend([el for el in href_elements if image_extension_validator(str(el))])

    # Build a list of tuples (XPath, link)
    page_images_tuples = []
    page_images_set = set()  # Use this set to ensure that we don't add the same image several times

    for el in image_elements:

        url = url_formatter(str(el), page_url)

        if url_validator(url) and url not in page_images_set:
            page_images_set.add(url)

            # Append a tuple (XPath, link)
            page_images_tuples.append((tree.getpath(el.getparent()), url))

    return page_images_tuples


def are_images_identical(hash_1, hash_2):
    """We estimate that two hashes represent the same image if 2 or less bits differ in their array representation"""

    return hash_1 - hash_2 < 3
