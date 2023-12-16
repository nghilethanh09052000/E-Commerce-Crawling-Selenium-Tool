from enum import Enum


class QueryType(str, Enum):
    GET_POST_DETAILS = 'get_post_details'
    GET_PROFILE_DETAILS = 'get_profile_details'
    GET_PROFILE_DETAILS_FROM_USER_ID = 'get_profile_details_from_user_id'
    GET_PROFILE_POSTS = 'get_profile_posts'
    GET_PROFILE_FOLLOWERS = 'get_profile_followers'
    GET_HASHTAG_POSTS = 'get_hashtag_posts'
    GET_CONSUMPTION_DETAILS = 'get_consumption_details'
