import difflib
from io import StringIO

import lxml.html


def get_tags(doc):
    """Get tags from a DOM tree

    Parameters:
    ===========
    doc: lxml parsed object
    """
    tags = list()

    root = doc.getroot()

    if root is None:
        return tags

    for el in root.iter():
        if isinstance(el, lxml.html.HtmlElement):
            tags.append(el.tag)
        elif isinstance(el, lxml.html.HtmlComment):
            tags.append("comment")
        else:
            raise ValueError("Don't know what to do with element: {}".format(el))

    return tags


def structural_similarity(document_1, document_2):
    """Computes the structural similarity between two DOM Trees

    Parameters:
    ===========
    document_1: html string
    document_2: html string

    Returns:
    ========
    similarity_score: int
    """
    try:
        document_1 = lxml.html.parse(StringIO(document_1))
        document_2 = lxml.html.parse(StringIO(document_2))
    except Exception as e:
        print(e)
        return 0

    tags1 = get_tags(document_1)
    tags2 = get_tags(document_2)
    diff = difflib.SequenceMatcher()
    diff.set_seq1(tags1)
    diff.set_seq2(tags2)

    return diff.ratio()
