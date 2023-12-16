from app import logger
from app.settings import redis, sentry_sdk
from uuid import uuid4
import json
from app.settings import (
    UPLOAD_REQUEST_EXPIRY,
    PROFILES_BATCH_EXPIRY,
    DOMAIN_WHO_IS_EXPIRY,
    DOMAIN_BUILT_WITH_EXPIRY,
    URL_LOG_WITH_EXPIRY,
)


class RedisDAO:
    def get(self, key):
        return redis.get(key)

    def exists(self, key):
        return redis.exists(key)

    def delete_by_key(self, key):
        redis.delete(key)

    def set_kv(self, k, v, expire=None):
        logger.info(f"set redis kv ({k}, {v}, {expire})")
        try:
            redis.set(k, v, ex=expire)
        except Exception as e:
            logger.error(f"Failed to set redis kv ({k}, {v}, {expire})")
            sentry_sdk.capture_exception(e)
            return False
        return True

    def get_posters_info_to_scrape(self):
        """Return posters that we should scrape the profile of"""

        cached_posters_keys = redis.keys(pattern="crawling_poster_info:*")

        return [(redis.get_by_key(key), key) for key in cached_posters_keys]

    def get_instagram_profiles_to_recrawl(self):
        """Return the names of Instagram posters that we should recrawl

        Returns:
            users_keys (list): list of tuples associating each user object with its Redis key
        """

        redis_profile_keys = redis.keys(pattern="ig_profile_crawling:*")

        users_keys = [(json.loads(redis.get(key)), key) for key in redis_profile_keys]

        return users_keys

    def set_posters_scraping_data(self, posters, domain_name):
        """Create identifiers for Posters to be scraped"""
        for poster, _ in posters:
            redis.set(f"{str(domain_name)}_poster_scraping:{uuid4()}", poster)

    def get_posters_scraping_data(self, domain_name, auto_delete=False):
        """Get identifiers for Posters to be scraped"""
        cached_poster_keys = redis.keys(pattern=f"{domain_name}_poster_scraping:*")
        posters = [redis.get(key) for key in cached_poster_keys]

        if auto_delete:
            # Delete messages from queue
            for key in cached_poster_keys:
                redis.delete(key)

        return posters

    def get_posts_recrawling(self):
        cached_posts_keys = redis.keys(pattern="recrawling:*")
        return [(redis.get(key), key) for key in cached_posts_keys]

    def set_post_scraping_data(self, posts, domain_name):
        """Create identifiers for Posters to be scraped"""
        for post, _ in posts:
            redis.set(f"{str(domain_name)}:{uuid4()}", post)

    def get_posts_to_scrape_by_domain(self, domain_name):
        cached_posts_keys = redis.keys(pattern=f"{domain_name}:*")
        cached_posts = [redis.get(key) for key in cached_posts_keys]
        posts = [json.loads(post) for post in cached_posts]

        # Delete messages from queue
        for key in cached_posts_keys:
            redis.delete(key)

        return posts

    def get_upload_requests(self):
        return redis.keys("upload_request:*")

    def get_upload_request(self, key):
        return json.loads(redis.get(key))

    def get_upload_running_status(self, key):
        return bool(int(redis.hget("running", key)))  # Evaluate an int value to a boolean

    def set_upload_running_status(self, upload_key):
        redis.hset("running", upload_key, 1)

    def set_upload_request_batch_request(self, key, body):
        return self.set_kv(key, body, UPLOAD_REQUEST_EXPIRY)

    def set_url_upload_status(self, upload_request_id, upload_id, status):
        key = f"scraping_status:{upload_request_id}:{upload_id}"
        return self.set_kv(key, status, UPLOAD_REQUEST_EXPIRY)

    def get_posters_posts_to_scrape(self):
        """Returns posters that we should scrape their posts"""

        cached_posters_keys = redis.keys(pattern="crawling_poster_posts:*")

        return [(redis.get(key), key) for key in cached_posters_keys]

    def set_instagram_profile_batch(self, users_keys_batch, batch_key):
        users = [user_key[0] for user_key in users_keys_batch]

        redis.set(batch_key, json.dumps(users))
        redis.expire(batch_key, PROFILES_BATCH_EXPIRY)

    def set_domain_name_who_is(self, domain_name, data):
        redis.set(f"who_is_{domain_name}", json.dumps(data))
        redis.expire(f"who_is_{domain_name}", DOMAIN_WHO_IS_EXPIRY)

    def get_domain_who_is(self, domain_name):
        domain_info = self.get(f"who_is_{domain_name}")
        if domain_info:
            return json.loads(domain_info)
        return None

    def set_domain_name_built_with(self, domain_name, data):
        redis.set(f"built_with_{domain_name}", json.dumps(data))
        redis.expire(f"built_with_{domain_name}", DOMAIN_BUILT_WITH_EXPIRY)

    def get_domain_built_with(self, domain_name):
        domain_info = self.get(f"built_with_{domain_name}")
        if domain_info:
            return json.loads(domain_info)
        return None

    def set_url_log(self, url, creation_date_timestamp):
        key = f"url_log_{creation_date_timestamp}"
        return self.set_kv(key, str(url), URL_LOG_WITH_EXPIRY)
