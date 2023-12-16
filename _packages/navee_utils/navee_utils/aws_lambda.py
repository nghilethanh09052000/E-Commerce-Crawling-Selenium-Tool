import json
import logging
from typing import Dict, List

from .errors import LambdaCallError


def invoke_lambda(
    function_name: str,
    request_payload: Dict,
    lambda_client,
    sentry_sdk,
    required_fields: List[str] = [],
    retries: int = 3,
):
    payload = json.dumps(request_payload)

    # Try 3 times to avoid being trapped by cold start of Lambda, which can generate timeouts
    for _ in range(retries):
        response = None
        last_exception = None

        try:
            response = lambda_client.invoke(
                FunctionName=function_name,
                Payload=payload,
            )
            response = response["Payload"]
            response = response.read()
            response = json.loads(response)

            if response.get("errorMessage"):
                raise LambdaCallError(response["errorMessage"])

            for required_field in required_fields:
                assert required_field in response, f"{required_field} not in response"

            return response

        except Exception as e:
            last_exception = e
            logging.error(f"Error calling lambda {function_name}: {repr(e)}")
            continue

    # Failed 3 times
    with sentry_sdk.push_scope() as scope:
        scope.set_extra("API response", response)
        scope.set_extra("Request payload", request_payload)
        scope.set_extra("Function name", function_name)
        sentry_sdk.capture_exception(last_exception)
