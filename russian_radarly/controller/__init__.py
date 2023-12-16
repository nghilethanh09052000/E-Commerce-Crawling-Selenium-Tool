import json
from datetime import datetime, timezone
import logging
from urllib.parse import quote

import requests
from database import QueryLog, Session
from dateutil.parser import parse as parse_date
from enumerator import QueryType
from exception import RussianRadarlyException
from rr_settings import API_TOKEN
from sqlalchemy.sql import func
from validator import (followers_schema, post_schema, posts_schema,
                       profile_details_schema, validate_output)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class RequestController():

    def __init__(self, query_type, extended_output=False) -> None:
        self.query_type = query_type
        self.extended_output = extended_output

    def datetime_to_string(self, value, format='%Y-%m-%d %H:%M:%S'):

        if value is None:
            return None

        return value.strftime(format)

    def get_proxy_response(self, ig_url: str, add_prefix=True) -> dict:

        if add_prefix:
            api_prefix = f"https://api2.indext.io/api/aut_api.php?token={API_TOKEN}"
            query = f"{api_prefix}&url={ig_url}"
        else:
            query = ig_url

        time_of_call = datetime.now(timezone.utc)

        response = requests.request("GET", query, timeout=30)

        response_time = round((datetime.now(timezone.utc) - time_of_call).total_seconds() * 1000)

        self.add_query_log(query, self.query_type, time_of_call, response_time, response)

        return response.json()

    def get_caption(self, node):

        if not node:
            # Return an empty caption is node is None
            return ""

        # There are two different types of outputs for the caption
        try:  # type 1
            edges = node["edges"]

            return edges[0]["node"]["text"] if edges else ""
        except KeyError:  # type 2
            return node["text"]

    def get_str_datetime_from_timestamp(self, timestamp):

        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def get_pictures(self, node):

        # There are two different types of outputs for the pictures
        if node.get("display_url"):  # Type 1

            # Initiatilize the list of pictures with the display URL (always existing)
            pictures = [node["display_url"]]

            # If there is a side car (multiple pictures), overwrite the list of pictures
            sidecar = node.get("edge_sidecar_to_children")
            if sidecar:
                pictures = [
                    edge["node"]["display_url"] for edge in sidecar["edges"]
                ]

        else:  # Type 2

            if node.get("image_versions2"):
                pictures = [node["image_versions2"]["candidates"][0]["url"]]

            # If there is a carousel (multiple pictures), overwrite the list of pictures
            carousel = node.get("carousel_media")
            if carousel:
                pictures = [
                    media["image_versions2"]["candidates"][0]["url"] for media in carousel
                ]

        return pictures

    def get_post_v1(self, node):

        post = {
            "shortcode": node["shortcode"],
            "is_video": node["is_video"],
            "is_clip": node.get("product_type") == "clips",  # whether the user has a story available
            "pictures": self.get_pictures(node),
            "owner": {"id": node["owner"]["id"]},
            "video_url": node.get("video_url", ""),
            "publication_datetime": self.get_str_datetime_from_timestamp(node["taken_at_timestamp"]),
            "caption": self.get_caption(node["edge_media_to_caption"]),
        }

        if self.extended_output:
            post["first_comments"] = self.get_comments(node["edge_media_to_parent_comment"])
            post["owner"] = self.get_owner_extended(node["owner"])
            post["likes_count"] = node["edge_media_preview_like"]["count"]

            if post["likes_count"] == -1 and len(node["edge_media_preview_like"]["edges"]) > 0:
                post["last_liked_by"] = self.get_owner_extended(node["edge_media_preview_like"]["edges"][0]["node"])

        return post

    def get_post_v2(self, node):

        post = {
            "shortcode": node["code"],
            "is_video": node.get("is_unified_video", False),
            "is_clip": node.get("product_type") == "clips",  # whether the user has a story available
            "pictures": self.get_pictures(node),
            "owner": {"id": str(node["user"]["pk"])},
            "video_url": node["video_versions"][0]["url"] if node.get("video_versions") else "",
            "publication_datetime": self.get_str_datetime_from_timestamp(node["taken_at"]),
            "caption": self.get_caption(node["caption"]),
        }

        if self.extended_output:
            post["owner"] = self.get_owner_extended(node["user"])
            if "preview_comments" in node:
                post["first_comments"] = self.get_comments(node["preview_comments"])
            if "like_count" in node:
                post["likes_count"] = node["like_count"]
                if post["likes_count"] == -1 and node.get("top_likes"):
                    post["last_liked_by"] = {
                        "username": node["top_likers"][0],
                        "profile_pic_url": "",
                    }

        return post

    def get_media(self, media_edge):

        posts = [self.get_post_v1(edge["node"]) for edge in media_edge["edges"]]

        return {
            "count": media_edge["count"],
            "page_info": media_edge["page_info"],
            "posts": posts,
        }

    def get_followers_edge(self, followers_edge):

        followers = [self.get_owner_extended(edge["node"]) for edge in followers_edge["edges"]]

        return {
            "count": followers_edge["count"],
            "page_info": followers_edge["page_info"],
            "followers": followers,
        }

    def get_comment(self, comment_edge):

        if comment_edge.get("id"):  # type 1
            return {
                "text": comment_edge["text"],
                "creation_datetime": self.get_str_datetime_from_timestamp(comment_edge["created_at"]),
                "owner": self.get_owner_extended(comment_edge["owner"]),
                "likes_count": comment_edge["edge_liked_by"]["count"],
                "replies_count": comment_edge["edge_threaded_comments"]["count"],
            }

        else:  # type 2
            return {
                "text": comment_edge["text"],
                "creation_datetime": self.get_str_datetime_from_timestamp(comment_edge["created_at"]),
                "owner": self.get_owner_extended(comment_edge["user"]),
                "likes_count": comment_edge["comment_like_count"],
                "replies_count": 0,  # we can not retrieve this information without an additional call
            }

    def get_comments(self, node):

        if type(node) is dict:  # type 1, the node is a dictionary
            comments = [self.get_comment(edge["node"]) for edge in node["edges"]]
        else:  # type 2, the node is a list
            comments = [self.get_comment(edge) for edge in node]

        return comments

    def get_owner_extended(self, node):

        if node.get("id"):  # type 1
            user_id = node["id"]
        else:  # type 2
            user_id = str(node["pk"])

        return {
            "id": user_id,
            "is_verified": node["is_verified"],
            "profile_pic_url": node["profile_pic_url"],
            "username": node["username"],
        }

    @validate_output(post_schema)
    def scrape_ig_post_from_shortcode(self, shortcode: str) -> dict:
        ig_url = f"https://api2.indext.io/api/media_short.php?token={API_TOKEN}&shortcode={shortcode}"
        api_output = self.get_proxy_response(ig_url, add_prefix=False)
        try:
            return self.get_post_v2(api_output["items"][0])
        except (KeyError, TypeError) as e:
            raise RussianRadarlyException(f"{repr(e)} | scrape_ig_post_from_shortcode response json: {api_output}")


    @validate_output(profile_details_schema)
    def scrape_ig_profile_details_from_user_id(self, profile_id: str) -> dict:
        ig_url = f"https://api2.indext.io/api/aut_userinfo.php?token={API_TOKEN}&userid={profile_id}"
        api_output = self.get_proxy_response(ig_url, add_prefix=False)
        try:
            user = api_output["user"]
            formatted_output = {
                "user": {
                    "user_id": str(user["pk"]),
                    "username": user["username"],
                    "profile_pic_url": user["profile_pic_url"],
                    "biography": user["biography"],
                    "full_name": user["full_name"],
                    "external_url": user["external_url"],
                    "followers_count": user["follower_count"],
                    "posts_count": user["media_count"],
                    "is_business_account": user["is_business"],
                    "is_professional_account": False,
                    "is_verified": user["is_verified"],
                    "followings_count": user["following_count"],
                    "has_story": False,
                    "reels_count": 0,
                    "videos_count": 0,
                },
                "media": {
                    "count": 0,
                    "page_info": {
                        "has_next_page": False,
                        "end_cursor": "",
                    },
                    "posts": [],
                },
            }
        except (KeyError, TypeError) as e:
            raise RussianRadarlyException(f"{repr(e)} | scrape_ig_profile_details_from_user_id response json: {api_output}")
        return formatted_output


    @validate_output(profile_details_schema)
    def scrape_ig_profile_details_from_username(self, username: str) -> dict:
        ig_url = f"https://api2.indext.io/api/public_userinfo.php?token={API_TOKEN}&user={username}"
        api_output = self.get_proxy_response(ig_url, add_prefix=False)
        try:
            user = api_output["data"]["user"]
            media = self.get_media(user["edge_owner_to_timeline_media"])
            formatted_output = {
                "user": {
                    "user_id": user["id"],
                    "username": user["username"],
                    "profile_pic_url": user["profile_pic_url"],
                    "biography": user["biography"],
                    "full_name": user["full_name"],
                    "external_url": user["external_url"],
                    "followers_count": user["edge_followed_by"]["count"],
                    "posts_count": user["edge_owner_to_timeline_media"]["count"],
                    "is_business_account": user["is_business_account"],
                    "is_professional_account": user["is_professional_account"],
                    "is_verified": user["is_verified"],
                    "followings_count": user["edge_follow"]["count"],
                    "has_story": user["has_clips"],
                    "reels_count": user["highlight_reel_count"],
                    "videos_count": user["edge_felix_video_timeline"]["count"],
                },
                "media": media,
            }
        except (KeyError, TypeError) as e:
            raise RussianRadarlyException(f"{repr(e)} | scrape_ig_profile_details_from_username response json: {api_output}")
        return formatted_output


    @validate_output(posts_schema)
    def scrape_ig_posts_from_profile(self, profile_id: int, end_cursor: str) -> 'list[dict]':
        ig_url = f"https://api2.indext.io/api/get_posts.php?token={API_TOKEN}&user_id={profile_id}&after={end_cursor if end_cursor else ''}"
        api_output = self.get_proxy_response(ig_url, add_prefix=False)
        try:
            user = api_output["data"]["user"]
            media = self.get_media(user["edge_owner_to_timeline_media"])
            formatted_output = {
                "media": media,
            }
        except (KeyError, TypeError) as e:
            raise RussianRadarlyException(f"{repr(e)} | scrape_ig_posts_from_profile response json: {api_output}")
        return formatted_output


    @validate_output(followers_schema)
    def scrape_ig_followers_from_profile(self, profile_id: int, end_cursor: str) -> 'list[dict]':
        json_variables = {
            "id": profile_id,
            "include_reel": True,
            "fetch_mutual": True,
            "first": 48,
            "after": end_cursor,
        }
        str_variables = json.dumps(json_variables).replace(" ", "")
        ig_followers_prefix = (
            "https://www.instagram.com/graphql/query/?query_hash=5aefa9893005572d237da5068082d8d5&variables="
        )
        ig_url = quote(ig_followers_prefix) + quote(str_variables)
        api_output = self.get_proxy_response(ig_url)
        try:
            user = api_output["data"]["user"]
            followers_edge = self.get_followers_edge(user["edge_followed_by"])
            formatted_output = {
                "followers_edge": followers_edge,
            }
        except (KeyError, TypeError) as e:
            raise RussianRadarlyException(f"{repr(e)} | scrape_ig_followers_from_profile response json: {api_output}")

        return formatted_output


    @validate_output(posts_schema)
    def scrape_ig_posts_from_hashtag(self, hashtag: str, end_cursor: str = None) -> 'list[dict]':
        ig_url = f"https://api2.indext.io/api/tag.php?token={API_TOKEN}&tag={hashtag}&after={end_cursor if end_cursor else ''}"
        api_output = self.get_proxy_response(ig_url, add_prefix=False)
        try:
            hashtag_data = api_output["data"]["hashtag"]
            media = self.get_media(hashtag_data["edge_hashtag_to_media"])
            formatted_output = {
                "media": media,
            }
        except (KeyError, TypeError) as e:
            raise RussianRadarlyException(f"{repr(e)} | scrape_ig_posts_from_hashtag response json: {api_output}")
        return formatted_output


    def add_query_log(
        self, query: str, query_type: QueryType, time_of_call: datetime, response_time: int, response: requests.models.Response,
    ) -> None:
        text = response.text
        code = response.status_code
        if not response.ok:
            status = "error"
        else:
            try:
                json_response = response.json()
                text = json_response.get("description")
                status = json_response.get("status", "ok")
                code = json_response.get("code", response.status_code)
            except:
                status = "error"
        try:
            with Session() as session:
                new_log = QueryLog(
                    query=query,
                    query_type=query_type,
                    time_of_call=time_of_call,
                    response_time=response_time,
                    status=status,
                    description=text,
                    code=code,
                )
                session.add(new_log)
                session.commit()
        except Exception as e:
            logger.error(f"DB: failed to log response {repr(e)}")
        if status == "error":
            raise RussianRadarlyException(f"bad response from rr | status_code: {code} | text: {text}")


    def get_consumption_details(self, period_start_str: str = None, period_end_str: str = None) -> dict:
        """how many calls, how many authenticated, what response time?

        Parameters:
        ===========
        period_start_str: str
            This datetime should be in UTC timezone
        period_end_str: str
            This datetime should be in UTC timezone
        """

        # Get the period over which we want to get the consumption details
        period_start = parse_date(period_start_str) if period_start_str else None
        period_end = parse_date(period_end_str) if period_end_str else None

        with Session() as session:
            call_records = session.query(
                QueryLog.id
            )

            if period_start:
                call_records = call_records.filter(QueryLog.time_of_call > period_start)

            if period_end:
                call_records = call_records.filter(QueryLog.time_of_call < period_end)

            nb_calls = call_records.count()

            average_response_time = call_records.with_entities(
                func.avg(QueryLog.response_time)
            ).first()[0]

            return {
                "period_start": self.datetime_to_string(period_start),
                "period_end": self.datetime_to_string(period_end),
                "nb_calls": nb_calls,
                "avg_response_time": int(round(average_response_time or 0)),
            }
