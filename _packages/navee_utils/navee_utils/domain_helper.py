from urllib.parse import urlparse
from tldextract import TLDExtract
from typing import List, Dict

# addition of "sa.com" as extra suffix to better handle olx.sa.com and similar other websites ending with sa.com
CustomTLDExtractor = TLDExtract(extra_suffixes=["sa.com", "com.be"])


def get_domain_name_from_url(url: str):
    """
    Function to extract domain name from url.
    This function removes subdomains in the general case (fr.facebook.com become facebook.com)
    but there are exceptions such as for carousell websites.
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

    if subdomain.endswith("facebook.com") and "facebook.com/marketplace" in url:
        return "facebook.com/marketplace"

    ## HANDLING OF GENERAL CASE
    _, domain, suffix = CustomTLDExtractor(subdomain)
    if suffix:
        return f"{domain}.{suffix}".lower()
    else:
        return f"{domain}".lower()


def get_domain_names_from_urls(urls: List[str]) -> Dict[str, str]:
    """Extract domain names from multiple URLs"""
    return {url: get_domain_name_from_url(url) for url in urls}


if __name__ == "__main__":
    print(
        get_domain_name_from_url(
            "https://web.facebook.com/marketplace/item/840099987688418"
        )
    )
