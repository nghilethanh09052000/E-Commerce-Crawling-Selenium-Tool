import os
import random
import re
import requests
from typing import Optional
import tempfile
import yaml

from app import sentry_sdk
from app.models.marshmallow.proxy import ProxiesSchema

from selenium_driver import logger
from selenium.common.exceptions import WebDriverException


def load_proxies_credentials() -> ProxiesSchema:
    with open("app/configs/proxies_credentials.yml", "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
    return ProxiesSchema().load(config)


class ProxyException(WebDriverException):
    """
    Thrown when the proxy is not working.
    """

    pass


class ProxyExtension:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %d
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        custom_dir = f"proxy-ext-{host}-{port}-{user}-{password}"
        self._dir = os.path.join(tempfile.gettempdir(), custom_dir)
        if os.path.isdir(self._dir):
            return
        os.makedirs(self._dir)
        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    # def __del__(self):
    #     shutil.rmtree(self._dir)


def get_proxy_port(port: int, port_range: str):
    if port:
        return port
    ports = get_proxy_ports(port, port_range)
    return random.choice(ports)


def get_proxy_ports(port: int, port_range: str):
    if port:
        return [port]
    else:
        assert port_range, "Invalid proxy credentials: port or port_range should be present"
    port_range_match = re.fullmatch(r"([0-9]+)-([0-9]+)", port_range.strip())
    if port_range_match:
        min_port = int(port_range_match.group(1))
        max_port = int(port_range_match.group(2))
        ports = list(range(min_port, max_port + 1))
        return ports
    raise ValueError(f"Invalid port_range string '{port_range}'")


def get_proxy_authentification_extension(proxy_name: Optional[str], proxy_country: Optional[str]):
    """
    Creates a Chrome extension that login automatically to proxies at start of the driver.
    https://stackoverflow.com/questions/55582136/how-to-set-proxy-with-authentication-in-selenium-chromedriver-python
    """

    if not proxies_credentials:
        raise RuntimeError("No proxies credentials found")

    if proxy_name and proxy_name in [proxy.name for proxy in proxies_credentials.proxies]:
        proxy = [proxy for proxy in proxies_credentials.proxies if proxy.name == proxy_name][0]
    else:
        proxy = random.choice(proxies_credentials.proxies)

    if proxy.switch_ip_url:
        logger.info(f"Switching IP address for proxy {proxy.name}")
        requests.get(proxy.switch_ip_url)

    proxy_country = proxy_country or proxy.default_country

    host = proxy.credentials.host.format(country=proxy_country)
    port = get_proxy_port(proxy.credentials.port, proxy.credentials.port_range)
    username = proxy.credentials.username.format(country=proxy_country)
    password = proxy.credentials.password.format(country=proxy_country)
    logger.info(f"Using proxy {proxy.name}: host='{host}'; port={port}; country='{proxy_country}'")

    proxy_extension = ProxyExtension(host, port, username, password)

    return proxy_extension.directory, proxy.name, proxy_country


def generate_extension_files(proxies_credentials):
    if not proxies_credentials:
        raise RuntimeError("No proxies credentials found")

    for proxy in proxies_credentials.proxies:
        sid_is_needed = any(
            "{sid}" in s
            for s in (
                proxy.credentials.host,
                proxy.credentials.username,
                proxy.credentials.password,
            )
        )
        assert (
            not sid_is_needed
        ), f"Using sid in proxy extension files ({proxy.name}) leads to disk overflow. TODO: remove unused dirs"
        proxy_country = proxy.default_country
        host = proxy.credentials.host.format(country=proxy_country)
        username = proxy.credentials.username.format(country=proxy_country)
        password = proxy.credentials.password.format(country=proxy_country)
        ports = get_proxy_ports(proxy.credentials.port, proxy.credentials.port_range)
        for port in ports:
            ProxyExtension(host, port, username, password)


proxies_credentials = None
try:
    proxies_credentials = load_proxies_credentials()
    generate_extension_files(proxies_credentials)
except Exception as e:
    logger.error(f"Error loading proxy credentials {repr(e)}")
    sentry_sdk.capture_exception(e)
