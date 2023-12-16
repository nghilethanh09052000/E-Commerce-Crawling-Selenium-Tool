import json

API_KEY = "qg8mJFrKNexU9u2vTG"


class LambdaError:
    status_code = 500

    def __new__(cls, message: str):
        return {"statusCode": cls.status_code, "body": json.dumps({"message": message})}


class UnauthorizedError(LambdaError):
    status_code = 403


# entrypoint for lambda
def handler(event, _):
    if event["queryStringParameters"].get("api-key", "") != API_KEY:
        return UnauthorizedError("Invalid api key")

    return event["headers"]["x-forwarded-for"]
