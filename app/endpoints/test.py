from pprint import pprint
from unittest import TestCase

from app import app
from app.settings import NAVEE_DRIVER_AUTHORIZATION_KEY


def test_driver_get():
    url = "https://www.example.com/"

    class TestClient(TestCase):
        def __init__(self):
            self.app = app
            self.client = self.app.test_client()
            self._ctx = self.app.test_request_context()
            self._ctx.push()

        def test(self):
            with self.client:
                headers = {"Content-Type": "application/json", "Authorization": f"{NAVEE_DRIVER_AUTHORIZATION_KEY}"}
                response = self.client.post(
                    "/api/driver",
                    json={"url": url, "just_return_html_content": True},
                    headers=headers,
                )
                json_output = response.get_json()
                pprint(json_output)

    client = TestClient()
    client.test()


def test_infex():
    page_url = "http://books.toscrape.com/"
    image_url = "http://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg"

    class TestClient(TestCase):
        def __init__(self):
            self.app = app
            self.client = self.app.test_client()
            self._ctx = self.app.test_request_context()
            self._ctx.push()

        def test(self):
            with self.client:
                headers = {"Content-Type": "application/json", "Authorization": f"{NAVEE_DRIVER_AUTHORIZATION_KEY}"}
                response = self.client.post(
                    "/api/driver/infex",
                    json={"page_url": page_url, "image_url": image_url},
                    headers=headers,
                )
                json_output = response.get_json()
                pprint(json_output)

    client = TestClient()
    client.test()


def test_taobao_cookies():
    class TestClient(TestCase):
        def __init__(self):
            self.app = app
            self.client = self.app.test_client()
            self._ctx = self.app.test_request_context()
            self._ctx.push()

        def test(self):
            with self.client:
                headers = {"Content-Type": "application/json", "Authorization": f"{NAVEE_DRIVER_AUTHORIZATION_KEY}"}
                response = self.client.get(
                    "/api/driver/taobao_cookies",
                    headers=headers,
                )
                json_output = response.get_json()
                pprint(json_output)

    client = TestClient()
    client.test()


if __name__ == "__main__":
    test_taobao_cookies()
