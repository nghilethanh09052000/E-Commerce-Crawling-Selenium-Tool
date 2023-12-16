import json

from settings import redis, LAMBDA_API_KEY


def build_response(body, code):
    return {"statusCode": code, "body": json.dumps(body)}


def _set(body):
    if (key := body.get("key")) is None:
        return build_response("No key provided.", 400)

    if (value := body.get("value")) is None:
        return build_response("No value provided.", 400)

    redis.set(key, value)

    if (expire := body.get("expire")) is not None:
        redis.expire(key, expire)

    return build_response("OK", 200)


def _delete(body):
    if (key := body.get("key")) is None:
        return "No key provided.", 400

    redis.delete(key)
    return build_response("OK", 200)


def _get(body):
    if (key := body.get("key")) is None:
        return build_response("No key provided.", 400)

    return build_response(redis.get(key), 200)


def _scan_iter(body):
    if (pattern := body.get("pattern")) is None:
        return build_response("No pattern provided.", 400)

    return build_response([i for i in redis.scan_iter(pattern)], 200)


def _keys(body):
    if (pattern := body.get("pattern")) is None:
        return build_response("No pattern provided.", 400)

    return build_response([i for i in redis.keys(pattern)], 200)


def _hset(body):
    if (name := body.get("name")) is None:
        return build_response("No name provided.", 400)

    if (key := body.get("key")) is None:
        return build_response("No key provided.", 400)

    if (value := body.get("value")) is None:
        return build_response("No value provided.", 400)

    redis.hset(name, key, value)
    return build_response("OK", 200)


def _hdel(body):
    if (name := body.get("name")) is None:
        return build_response("No name provided.", 400)

    if (key := body.get("key")) is None:
        return build_response("No key provided.", 400)

    redis.hdel(name, key)
    return build_response("OK", 200)


def _hget(body):
    if (name := body.get("name")) is None:
        return build_response("No name provided.", 400)

    if (key := body.get("key")) is None:
        return build_response("No key provided.", 400)

    return build_response(redis.hget(name, key), 200)


def _hkeys(body):
    if (name := body.get("name")) is None:
        return build_response("No name provided.", 400)

    return build_response([i for i in redis.hkeys(name)], 200)


fn_by_name = {
    "set": _set,
    "delete": _delete,
    "get": _get,
    "scan_iter": _scan_iter,
    "keys": _keys,
    "hset": _hset,
    "hdel": _hdel,
    "hget": _hget,
    "hkeys": _hkeys,
}


# entrypoint for lambda
def handler(event, _):
    x_api_key = event["headers"].get("x-api-key")
    if not x_api_key or x_api_key != LAMBDA_API_KEY:
        return build_response("Unauthorized", 401)

    body = json.loads(event["body"])

    if (fn_name := body.get("fn_name")) is None:
        return build_response("No fn_name provided.", 400)

    if fn_name not in fn_by_name:
        return build_response("Invalid fn_name.", 400)

    return fn_by_name[fn_name](body)


if __name__ == "__main__":
    t = redis.get("test")
    print(t)
