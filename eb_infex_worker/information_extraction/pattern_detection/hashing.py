import random
import time
from io import BytesIO
from multiprocessing import Manager, Process

import imagehash
import requests
from fake_useragent import FakeUserAgent
from PIL import Image

# Set a user agent to impersonate a normal browser session
ua = FakeUserAgent(fallback="Mozilla/5.0 (X11; OpenBSD amd64; rv:28.0) Gecko/20100101 Firefox/28.0")


def compute_image_hash(image_url):
    """Build the hash of an image

    imagehash.dhash is a difference hashing (https://tech.okcupid.com/evaluating-perceptual-image-hashes-okcupid/)
    """

    r = requests.get(
        image_url,
        headers={"User-Agent": ua.random},
        allow_redirects=True,
        timeout=2,
    )

    image_hash = imagehash.dhash(Image.open(BytesIO(r.content)))

    return image_hash


def compute_hash_worker(xpath, image_url, live_hash_list):
    """Compute the hash of an image URL and add it to a manager list shared across processes

    Parameters:
    ===========
    xpath: str
        not used in the function but input and output to keep it grouped with the image URL
    image_url: str
        image for which we compute a hash
    live_hash_list: multiprocessing manager list containing tuples (XPath, hash)
        list shared by all manager's processes, to which we can append element in a thread-safe way
    """

    time.sleep(random.random())
    try:
        hash = compute_image_hash(image_url)
        live_hash_list.append((xpath, hash))
    except (OSError, IOError):
        pass

    return live_hash_list  # hash is normally an array but it can be used as a string


def compute_images_hashes_threaded(image_list):
    """
    Compute hashes of image URLs in image_list in a multi-threaded way

    Parameters:
    ===========
    image_list: tuple[]
        (XPath, URL) for which we want to compute hashes

    Returns:
    ========
    live_hash_list: tuple[]
        list of hashes for every URL in image_list (XPath, URL, hash)
    """

    live_hash_list = []

    with Manager() as manager:

        manager_live_hash_list = manager.list()
        processes = []

        for xpath, image_url in image_list:
            # We pass the manager's list to each process
            p = Process(target=compute_hash_worker, args=(xpath, image_url, manager_live_hash_list))

            p.start()
            processes.append(p)

        # Wait for every process to terminate
        for p in processes:
            p.join()

        live_hash_list = list(manager_live_hash_list)

    return live_hash_list
