import requests
from app.settings import NAVEE_DRIVER_API_URL, NAVEE_DRIVER_API_TIMEOUT, NAVEE_DRIVER_AUTHORIZATION_KEY


def get_url_data(body):
    headers = {"Content-Type": "application/json", "Authorization": f"{NAVEE_DRIVER_AUTHORIZATION_KEY}"}
    response = requests.post(
        f"{NAVEE_DRIVER_API_URL}/driver", json=body, headers=headers, timeout=NAVEE_DRIVER_API_TIMEOUT
    )

    if response:
        return response.json()

    return None
