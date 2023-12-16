from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

from lxml import etree
from selenium.common.exceptions import WebDriverException

from tldextract import TLDExtract


image_extensions = ["jpg", "png", "gif", "jpeg", "webp"]


def url_validator(url):
    """Determines whether a URL is valid"""

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc, result.path]) and "javascript:void(0)" not in url
    except Exception:
        return False


def url_formatter(url, page_url):
    """Ensure that URLs are absolute by using urljoin()

    If the URL is already complete (with an https:// etc.) nothing happens
    If the link found is partial (i.e. /ventes instead of https://www.leboncoin.fr/ventes), complete it
    """

    if not url_validator(url):

        # Ensure that URLs are absolute
        if not url.startswith("http") and not url.startswith("/"):
            url = urljoin(page_url, "/" + url)
        else:
            url = urljoin(page_url, url)

    # Unquote every image URL, i.e. decode from percent-encoded data to UTF-8 ("%C3%A9" to "  ")
    url = unquote(url)

    return url


def image_extension_validator(link):
    # Check whether the image extension is among the extensions defined in image_extensions
    return urlparse(link.strip().lower()).path.split(".")[-1] in image_extensions


def stringify_tree_element(node):
    """Converts a tree element to string and decode it (useful to print and to compute similarities)"""

    if node is None:
        return ""

    try:
        stringified_node = etree.tostring(node).decode("utf-8")
    except Exception:
        print("Exception in tree element stringification")
        stringified_node = ""

    return stringified_node


def is_driver_live(driver):
    """Determines whether the driver has been closed or destroyed in any way

    Returns:
    ========
    bool: True if the driver is accessible else False
    """

    try:
        driver.title
        return True
    except WebDriverException:
        return False


def prune_domain(url):
    """Remove the start substring of url which contains the scheme and network location information

    Returns:
    ========
    pruned_url: str
        if a domain and a suffix are detected, return the part of url that comes after domain.suffix
        else return the url unchanged
    """

    domain_name = get_domain_name_from_url(url)

    if domain_name:
        # limit the number of splits to 1 and get what comes after this split
        url = url.split(domain_name, 1)[1]

    if url.startswith("/"):
        url = url[1:]

    return url


market_places = {
    "carousell.com.my": {
        "post_path": "https://www.carousell.com.my/p/",
        "search_path": ["https://www.carousell.com.my/search/"],
    },
    "olx.co.ug": {"post_path": "https://www.jiji.ug/", "search_path": ["https://jiji.ug/search?query="]},
    "kidstaff.com.ua": {
        "post_path": "https://kidstaff.com.ua/",
        "search_path": ["https://www.kidstaff.com.ua/search/words-"],
    },
    "tiu.ru": {"post_path": "https://tiu.ru/", "search_path": ["https://tiu.ru/search?search_term="]},
    "dolap.com": {"post_path": "https://dolap.com/urun/", "search_path": ["https://dolap.com/ara?q="]},
    "ruten.com.tw": {
        "skip_query_string_cleaning": True,
        "post_path": "https://www.ruten.com.tw/item/",
        "search_path": ["https://www.ruten.com.tw/find/?q="],
    },
    "tw.carousell.com": {
        "post_path": "https://tw.carousell.com/p/",
        "search_path": ["https://tw.carousell.com/search/"],
    },
    "depop.com": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "carousell.sg": {"post_path": "https://www.carousell.sg/p/", "search_path": ["https://www.carousell.sg/search/"]},
    "bakeca.it": {
        "post_path": "https://www.bakeca.it/annunci",
        "search_path": ["https://www.bakeca.it/annunci/tutte-le-categorie/?keyword="],
    },
    "olx.com.pk": {"post_path": "https://www.olx.com.pk/item/", "search_path": ["https://www.olx.com.pk/items/q-"]},
    "olx.com.kw": {"post_path": "https://olx.com.kw/ad/", "search_path": ["https://olx.com.kw/ads/q-"]},
    "olx.in": {"post_path": "https://www.olx.in/item/", "search_path": ["https://www.olx.in/items/q-"]},
    "zakupka.com": {"post_path": "https://zakupka.com/p/", "search_path": ["https://zakupka.com/all/poisk/?poisk="]},
    "bidorbuy.co.za": {
        "post_path": "https://www.bidorbuy.co.za/item/",
        "search_path": ["https://www.bidorbuy.co.za/search/"],
    },
    "shopee.sg": {"post_path": "https://shopee.sg/", "search_path": ["https://shopee.sg/search?keyword="]},
    "olx.com.co": {"post_path": "https://www.olx.com.co/item/", "search_path": ["https://www.olx.com.co/items/q-"]},
    "subito.it": {
        "post_path": "https://www.subito.it/",
        "search_path": ["https://www.subito.it/annunci-italia/vendita/usato/?q="],
    },
    "shopee.co.id": {
        "post_path": "https://shopee.co.id/",
        "search_path": ["https://shopee.co.id/search?keyword=", "/search?"],
    },
    "olx.ua": {
        "post_path": "https://www.olx.ua/",
        "search_path": ["https://www.olx.ua/list/q-"],
        "localisation_country_list": ["uk"],
    },
    "olx.bg": {"post_path": "https://www.olx.bg/ad/", "search_path": ["https://www.olx.bg/ads/q-"]},
    "depop.com.us": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "olx.ba": {"post_path": "https://www.olx.ba/artikal/", "search_path": ["https://www.olx.ba/pretraga?trazilica="]},
    "vinted.de": {
        "post_path": "https://www.vinted.de/",
        "search_path": ["https://www.vinted.de/vetements?search_text="],
    },
    "olx.sa.com": {"post_path": "https://olx.sa.com/ad/", "search_path": ["https://olx.sa.com/ads/q-"]},
    "olx.com.pe": {"post_path": "https://www.olx.com.pe/item/", "search_path": ["https://www.olx.com.pe/items/q-"]},
    "redbubble.com": {
        "post_path": "https://www.redbubble.com/i/",
        "search_path": ["https://www.redbubble.com/shop/?query="],
    },
    "ebay.com": {"post_path": None, "search_path": ["https://www.ebay.com/sch/i.html?_nkw="]},
    "tokopedia.com": {
        "post_path": "https://www.tokopedia.com/",
        "search_path": ["https://www.tokopedia.com/search?st=product&q="],
    },
    "depop.com.de": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "taobao.com": {
        "post_path": "https://detail.tmall.com/item.htm?id=",
        "search_path": ["https://s.taobao.com/search?q="],
    },
    "vinted.pl": {"post_path": "https://www.vinted.pl/", "search_path": ["https://www.vinted.pl/ubrania?search_text="]},
    "depop.com.it": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "bonanza.com": {
        "post_path": "https://www.bonanza.com/listings/",
        "search_path": ["https://www.bonanza.com/items/search?q[search_term]="],
    },
    "olx.com.lb": {"post_path": "https://olx.com.lb/ad/", "search_path": ["https://olx.com.lb/ads/q-"]},
    "lazada.com.ph": {"post_path": None, "search_path": ["https://www.lazada.com.ph/catalog/?q="]},
    "shopee.co.th": {
        "post_path": "https://shopee.co.th/",
        "search_path": ["https://shopee.co.th/search?keyword=", "/search?"],
    },
    "wish.com": {"post_path": "https://www.wish.com/product/", "search_path": ["https://www.wish.com/search/"]},
    "220.lv": {
        "query_string_to_keep": ["id"],
        "post_path": "https://220.lv/lv/",
        "search_path": ["https://220.lv/lv/search?q="],
    },
    "olx.kz": {"post_path": "https://www.olx.kz/obyavlenie/", "search_path": ["https://www.olx.kz/list/q-"]},
    "vinted.lt": {
        "post_path": "https://www.vinted.lt/",
        "search_path": ["https://www.vinted.lt/vetements?search_text="],
    },
    "buyma.com": {"post_path": "https://www.buyma.com/item/", "search_path": ["https://www.buyma.com/r/-F1/"]},
    "shafa.ua": {"post_path": "https://shafa.ua/", "search_path": ["https://shafa.ua/clothes?search_text="]},
    "depop.com.au": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "avito.ru": {"post_path": "https://www.avito.ru/", "search_path": ["https://www.avito.ru/rossiya?q="]},
    "olx.pl": {"post_path": "https://www.olx.pl/oferta/", "search_path": ["https://www.olx.pl/oferty/q-"]},
    "ceasuridemana.ro": {"post_path": "http://ceasuridemana.ro/", "search_path": ["http://ceasuridemana.ro/"]},
    "tmon.co.kr": {
        "post_path": "http://www.tmon.co.kr/deal/",
        "search_path": ["https://search.tmon.co.kr/search/?keyword="],
    },
    "nz.carousell.com": {
        "post_path": "https://nz.carousell.com/p/",
        "search_path": ["https://nz.carousell.com/search/"],
    },
    "id.carousell.com": {
        "post_path": "https://id.carousell.com/p/",
        "search_path": ["https://id.carousell.com/search/"],
    },
    "olx.ro": {"post_path": "https://www.olx.ro/oferta/", "search_path": ["https://www.olx.ro/oferte/q-"]},
    "olx.com.gt": {
        "post_path": "https://www.encuentra24.com/guatemala-es/",
        "search_path": ["https://www.encuentra24.com/guatemala-es/searchresult/all?q=keyword."],
    },
    "fril.jp": {"post_path": "https://item.fril.jp/", "search_path": ["https://fril.jp/search/"]},
    "depop.com.uk": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "olx.com.eg": {"post_path": "https://olx.com.eg/ad/", "search_path": ["https://olx.com.eg/ads/q-"]},
    "au.carousell.com": {
        "post_path": "https://au.carousell.com/p/",
        "search_path": ["https://au.carousell.com/search/"],
    },
    "kupujemprodajem.com": {
        "post_path": "https://www.kupujemprodajem.com/",
        "search_path": ["https://www.kupujemprodajem.com/search.php?"],
    },
    "bazos.sk": {"post_path": None, "search_path": ["https://www.bazos.sk/search.php?hledat="]},
    "carousell.ph": {"post_path": "https://www.carousell.ph/p/", "search_path": ["https://www.carousell.ph/search/"]},
    "olx.com.om": {"post_path": "https://olx.com.om/ad/", "search_path": ["https://olx.com.om/ads/q-"]},
    "labellov.com": {
        "post_path": "https://www.labellov.com/",
        "search_path": ["https://www.labellov.com/catalogsearch/result/?q="],
    },
    "ca.carousell.com": {
        "post_path": "https://ca.carousell.com/p/",
        "search_path": ["https://ca.carousell.com/search/"],
    },
    "bukalapak.com": {"post_path": None, "search_path": ["https://www.bukalapak.com/products?search%5Bkeywords%5D="]},
    "shopee.com.my": {
        "post_path": "https://shopee.com.my/",
        "search_path": ["https://shopee.com.my/search?keyword=", "/search?"],
    },
    "vinted.com": {
        "post_path": "https://www.vinted.com/",
        "search_path": ["https://www.vinted.com/clothes?search_text="],
    },
    "vestiairecollective.com": {"post_path": None, "search_path": ["https://www.vestiairecollective.com/search/?q="]},
    "olx.com.ec": {"post_path": "https://www.olx.com.ec/item/", "search_path": ["https://www.olx.com.ec/items/q-"]},
    "olx.co.id": {"post_path": "https://www.olx.co.id/item/", "search_path": ["https://www.olx.co.id/items/q-"]},
    "olx.pt": {"post_path": "https://www.olx.pt/anuncio/", "search_path": ["https://www.olx.pt/ads/q-"]},
    "klubok.com": {"post_path": "https://klubok.com/", "search_path": ["https://klubok.com/?q="]},
    "olx.com.ar": {"post_path": "https://www.olx.com.ar/item/", "search_path": ["https://www.olx.com.ar/items/q-"]},
    "olx.co.cr": {
        "post_path": "https://www.encuentra24.com/costa-rica-es/",
        "search_path": ["https://www.encuentra24.com/costa-rica-es/searchresult/"],
    },
    "olx.co.za": {"post_path": "https://www.olx.co.za/item/", "search_path": ["https://www.olx.co.za/items/q-"]},
    "olx.uz": {"post_path": "https://www.olx.uz/obyavlenie/", "search_path": ["https://www.olx.uz/list/q-"]},
    "carousell.com.hk": {
        "post_path": "https://www.carousell.com.hk/p/",
        "search_path": ["https://www.carousell.com.hk/search/"],
    },
    "jd.hk": {"post_path": "https://npcitem.jd.hk/", "search_path": ["https://search.jd.hk/Search?keyword="]},
    "vinted.co.uk": {
        "post_path": "https://www.vinted.co.uk/",
        "search_path": ["https://www.vinted.co.uk/vetements?search_text="],
    },
    "rakuten.co.jp": {"post_path": None, "search_path": ["https://search.rakuten.co.jp/search/mall/"]},
    "olx.com.pa": {
        "post_path": "https://www.encuentra24.com/panama-es/",
        "search_path": ["https://www.encuentra24.com/panama-es/searchresult/"],
    },
    "bigl.ua": {"post_path": "https://bigl.ua/p", "search_path": ["https://bigl.ua/search?search_term="]},
    "lazada.sg": {"post_path": None, "search_path": ["https://www.lazada.sg/catalog/?q="]},
    "shopee.tw": {"post_path": "https://shopee.tw/", "search_path": ["https://shopee.tw/search?keyword=", "/search?"]},
    "olx.com.bh": {"post_path": "https://olx.com.bh/ad/", "search_path": ["https://olx.com.bh/ads/q-"]},
    "olx.com.br": {"post_path": "https://am.olx.com.br/", "search_path": ["https://www.olx.com.br/brasil?q="]},
    "shopee.ph": {"post_path": "https://shopee.ph/", "search_path": ["https://shopee.ph/search?keyword=", "/search?"]},
    "olx.com.sv": {
        "post_path": "https://www.encuentra24.com/el-salvador-es/",
        "search_path": ["https://www.encuentra24.com/el-salvador-es/searchresult/all?q=keyword."],
    },
    "shopee.vn": {"post_path": "https://shopee.vn/", "search_path": ["https://shopee.vn/search?keyword=", "/search?"]},
    "vinted.cz": {
        "post_path": "https://www.vinted.cz/",
        "search_path": ["https://www.vinted.cz/predmety?search_text="],
    },
    "bazar.bg": {"post_path": "https://bazar.bg/", "search_path": ["https://bazar.bg/obiavi?&q="]},
    "allegro.pl": {"post_path": "https://www.allegro.pl/", "search_path": ["https://www.allegro.pl/listing?string="]},
    "vinted.fr": {
        "post_path": "https://www.vinted.fr/",
        "search_path": ["https://www.vinted.fr/vetements?search_text="],
    },
    "lazada.co.id": {"post_path": None, "search_path": ["https://www.lazada.co.id/catalog/?q="]},
    "vinted.it": {
        "post_path": "https://www.vinted.it/",
        "search_path": ["https://www.vinted.it/vetements?search_text="],
    },
    "jd.com": {"post_path": "https://item.jd.com/", "search_path": ["https://search.jd.com/Search?keyword="]},
    "dhgate.com": {
        "post_path": "https://www.dhgate.com/product/",
        "search_path": [
            "https://pt.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://de.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://tr.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://kr.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://ar.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://es.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://ru.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://it.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://fr.dhgate.com/wholesale/search.do?act=search&searchkey",
            "https://www.dhgate.com/wholesale/search.do?act=search&searchkey",
        ],
    },
    "2dehands.be": {"post_path": "https://www.2dehands.be/a/", "search_path": ["https://www.2dehands.be/q/"]},
    "depop.com.fr": {"post_path": None, "search_path": ["https://www.depop.com/search/?q="]},
    "etsy.com": {"post_path": "https://www.etsy.com/listing", "search_path": ["https://www.etsy.com/search?q="]},
    "prom.ua": {"post_path": "https://prom.ua/", "search_path": ["https://prom.ua/search?search_term="]},
}

# addition of "sa.com" as extra suffix to better handle olx.sa.com and similar other websites ending with sa.com
CustomTLDExtractor = TLDExtract(extra_suffixes=["sa.com"])


def get_domain_name_from_url(url):
    """
    Function to extract domain name from url.
    This function removes subdomains in the general case (fr.facebook.com become facebook.com)
    but there are exceptions such as for carousell websites.

    Args:
        url:

    Returns:
    """

    if "http" not in url:
        url = f"https://{url}"

    subdomain = urlparse(url).netloc

    ## HANDLING OF EXCEPTIONS
    if subdomain.endswith("au.carousell.com"):
        return "au.carousell.com"
    if subdomain.endswith("nz.carousell.com"):
        return "nz.carousell.com"
    if subdomain.endswith("tw.carousell.com"):
        return "tw.carousell.com"
    if subdomain.endswith("id.carousell.com"):
        return "id.carousell.com"
    if subdomain.endswith("ca.carousell.com"):
        return "ca.carousell.com"

    ## HANDLING OF GENERAL CASE
    _, domain, suffix = CustomTLDExtractor(subdomain)
    if suffix:
        return f"{domain}.{suffix}".lower()
    else:
        return f"{domain}".lower()


def remove_localization(url, localisation_country_list):
    """
    For domains that have country codes in path that have
    no impact on content Example: product/uk/item.html --> /product/item.html
    """
    url_parts = url.split("/")
    for url_part in url_parts:
        if url_part.lower() in localisation_country_list:
            url = url.replace(f"/{url_part}", "")
    return url


def clean_post_url(url):
    """
    Function's role is to check if the url belongs to one of the scraped marketplace listing
    and if the url is not a search result we remove unexecessary query strings granted the marketplace
    doesn't use query string in its page rendering. Example pass post id as query string

    Goal= Avoid duplications due to query string

    """
    try:
        marketplace_listings = [
            key for (key, value) in market_places.items() if value.get("skip_query_string_cleaning", False) is False
        ]

        domain_name = get_domain_name_from_url(url)
        if domain_name in marketplace_listings:
            domain_config = market_places[domain_name]
            # check if url is search result link, then we cant remove query strings
            for entry in domain_config.get("search_path"):
                if url.startswith(entry):
                    return url

            # if not search result then clean post url
            post_url_path = domain_config.get("post_path")
            query_string_to_keep = domain_config.get("query_string_to_keep", [])
            localisation_country_list = domain_config.get("localisation_country_list", [])

            query_string_to_add = {}
            if len(query_string_to_keep) > 0:
                parsed_url = urlparse(url)
                query_strings_in_url = parse_qs(parsed_url.query)
                if len(query_strings_in_url) > 0:
                    for entry in query_string_to_keep:
                        if entry in query_strings_in_url:
                            query_string_to_add[entry] = query_strings_in_url[entry][0]

            # check if url is a valid post url if exists in setings
            if post_url_path is None or url.startswith(post_url_path):
                try:
                    url = url.split("?")[0]
                    if len(query_string_to_add) > 0:
                        url = f"{url}?{urlencode(query_string_to_add)}"
                    if localisation_country_list:
                        url = remove_localization(url, localisation_country_list)
                except Exception as ex:
                    print(ex)

            # remove any ending / in urls
            if url[-1] == "/":
                url = url[:-1]
        return url
    except Exception as ex:
        print(f"Error on url:{url} clean_post_url {ex}")
        return url
