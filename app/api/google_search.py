"""
Programmable Search Engine doc: https://developers.google.com/custom-search/v1/using_rest

Programmable Search Control Panel: https://cse.google.com/all

We use the Custom Search Site Restricted JSON API to get an unlimited daily quota of searches.

-> example query: https://www.googleapis.com/customsearch/v1/siterestrict?cx=fecbe1f738b60147a&key=AIzaSyB0Xl3huOnidQ315krDtpY1qg0wfScyKQ0&q=salut&start=10&sort=date:r:20010101:20211231
-> limit: we can't search for more than 100 results per query

API reference: https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list#request

-> excludeTerms (Identifies a word or phrase that should not appear in any documents in the search results)
-> hq (Appends the specified query terms to the query, as if they were combined with a logical AND operator)
-> orTerms (Provides additional search terms to check for in a document, where each document in the search results must contain at least one of the additional search terms)  # noqa:E501
-> sort=date:r:20010101:20211231

Monitoring: https://console.cloud.google.com/apis/dashboard?project=luxury-application

The number of results can vary when running consecutively multiple times the same search.

What we are able to get from the results:
* URL
* partial caption
* nb of likes
* nb of comments
* 1 image URL
* poster name
"""

from datetime import datetime

import requests

from app.settings import (
    GOOGLE_POST_SEARCH_CX,
    GOOGLE_SEARCH_KEY,
    GOOGLE_PROFILE_SEARCH_CX,
)


def call_custom_search_api(
    search_type,
    q: str,
    page: int = 1,
    hqs: list = [],
    orTerms: list = [],
    start_date: datetime = None,
    end_date: datetime = None,
) -> dict:

    assert search_type in ("post", "profile")

    google_search_cx = GOOGLE_POST_SEARCH_CX if search_type == "post" else GOOGLE_PROFILE_SEARCH_CX
    search_url = (
        f"https://www.googleapis.com/customsearch/v1/siterestrict?cx={google_search_cx}&key={GOOGLE_SEARCH_KEY}&q={q}"
    )

    # hq appends the specified query terms to the query, as if they were combined with a logical AND operator
    for hq in hqs:
        search_url += f"&hq={hq}"

    # orTerms provides additional search terms to check for in a document,
    # where each document in the search results must contain at least one of the additional search terms
    for orTerm in orTerms:
        search_url += f"&orTerms={orTerm}"

    # Sort by descending date (of indexing, I guess)
    date_parameter = "&sort=date"

    # Add the date constraint if any is provided (^ is the XOR operator)
    if (start_date is None) ^ (end_date is None):
        raise ValueError("start_date and end_date parameters must be both null or both not null")

    if start_date:
        start_date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")

        date_parameter += f":r:{start_date_str}:{end_date_str}"

    search_url += date_parameter

    # Add the pagination
    search_url += f"&start={(page - 1) * 10}"

    res = requests.get(search_url).json()

    return res


def google_post_search(query):

    res = call_custom_search_api("post", query)

    # Surprisingly, totalResults is 0 if there are no results in a given page
    # Thus, total_results is only accurate at the first page search
    total_results = int(res["searchInformation"]["totalResults"])

    ig_shortcodes = [item["formattedUrl"].split("/p/")[1].split("/")[0] for item in res.get("items", [])]

    # We cannot retrieve more than 10 posts per page neither more than 100 results for a given query
    nb_of_pages = min(1 + ((total_results - 1) // 10), 10)

    for page_nb in range(2, nb_of_pages + 1):
        res = call_custom_search_api("post", query, page=page_nb)

        ig_shortcodes.extend([item["formattedUrl"].split("/p/")[1].split("/")[0] for item in res.get("items", [])])

    return list(set(ig_shortcodes))


def google_profile_search(query):

    res = call_custom_search_api("profile", query)

    # Surprisingly, totalResults is 0 if there are no results in a given page
    # Thus, total_results is only accurate at the first page search
    total_results = int(res["searchInformation"]["totalResults"])

    ig_usernames = [item["formattedUrl"].split("www.instagram.com/")[-1].split("/")[0] for item in res.get("items", [])]

    # We cannot retrieve more than 10 posts per page neither more than 100 results for a given query
    nb_of_pages = min(1 + ((total_results - 1) // 10), 10)

    for page_nb in range(2, nb_of_pages + 1):
        res = call_custom_search_api("profile", query, page=page_nb)

        ig_usernames.extend(
            [item["formattedUrl"].split("www.instagram.com/")[-1].split("/")[0] for item in res.get("items", [])]
        )

    return list(set(ig_usernames))


if __name__ == "__main__":

    import sys

    # The first script argument is the query type: post of profile
    query_type = sys.argv[1]

    # The second script argument is the query itself (use quotation marks to include whitespaces)
    q = "station f"
    if len(sys.argv) > 2:
        q = sys.argv[2]

    print(f'Running a Google search on Instagram {query_type}s with the query "{q}"')

    if query_type == "post":
        results = google_post_search(q)
    elif query_type == "profile":
        results = google_profile_search(q)

    print(f"Retrieved {len(results)} distinct results: {sorted(results)}")
