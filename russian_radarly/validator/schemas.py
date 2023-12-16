user_schema = {
    "type": "object",
    "properties": {
        "biography": {"type": "string"},
        "username": {"type": "string"},
        "user_id": {"type": "string"},
        "profile_pic_url": {"type": "string"},
        "is_business_account": {"type": "boolean"},
        "is_professional_account": {"type": "boolean"},
        "is_verified": {"type": "boolean"},
        "full_name": {"type": "string"},
        "external_url": {"type": ["string", "null"]},
        "followers_count": {"type": "integer"},
        "posts_count": {"type": "integer"},
    },
    "required": [
        "biography", "username", "user_id", "profile_pic_url", "is_business_account", "is_professional_account",
        "is_verified", "full_name", "external_url", "followers_count", "posts_count",
    ],
}

owner_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
    },
    "required": ["id"],
}

extended_owner_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "is_verified": {"type": "boolean"},
        "profile_pic_url": {"type": "string"},
        "username": {"type": "string"},
    },
    "required": ["id", "is_verified", "profile_pic_url", "username"],
}

page_info_schema = {
    "type": "object",
    "properties": {
        "has_next_page": {"type": "boolean"},
        "end_cursor": {"type": "string"},
    },
    "required": ["has_next_page", "end_cursor"],
}

comment_schema = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "creation_datetime": {"type": "string"},
        "owner": extended_owner_schema,
        "likes_count": {"type": "integer"},
        "replies_count": {"type": "integer"},
    },
    "required": [
        "text",
        "creation_datetime",
        "owner",
        "likes_count",
        "replies_count",
    ],
}

post_schema = {
    "type": "object",
    "properties": {
        "shortcode": {"type": "string"},
        "is_video": {"type": "boolean"},
        "is_clip": {"type": "boolean"},
        "caption": {"type": "string"},
        "video_url": {"type": "string"},
        "pictures": {
            "type": "array",
            "items": {"type": "string"},
        },
        "publication_datetime": {"type": "string"},
        "likes_count": {"type": "integer"},
        "owner": owner_schema,
        "first_comments": {
            "type": "array",
            "items": comment_schema,
        },
    },
    "required": [
        "shortcode",
        "is_video",
        "is_clip",
        "caption",
        "video_url",
        "pictures",
        "owner",
    ],
}

media_schema = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "page_info": page_info_schema,
        "posts": {
            "type": "array",
            "items": post_schema,
        },
    },
    "required": ["count", "page_info", "posts"],
}

profile_details_schema = {
    "type": "object",
    "properties": {
        "user": user_schema,
        "media": media_schema,
    },
    "required": ["user", "media"],
}

posts_schema = {
    "type": "object",
    "properties": {
        "media": media_schema,
    },
    "required": ["media"],
}

followers_edge_schema = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "page_info": page_info_schema,
        "followers": {
            "type": "array",
            "items": extended_owner_schema,
        },
    },
    "required": ["count", "page_info", "followers"],
}

followers_schema = {
    "type": "object",
    "properties": {
        "followers_edge": followers_edge_schema,
    },
    "required": ["followers_edge"],
}
