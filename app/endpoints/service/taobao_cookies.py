import time

from selenium import webdriver

from app import logger


def retrieve_cookies():
    logger.info("Getting the initial cookies")

    # Set up Selenium
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    # First, get the _m_h5_tk and _m_h5_tk_enc cookies
    url = "https://world.taobao.com/"
    driver.get(url)
    time.sleep(2)
    m_h5_tk = driver.get_cookie("_m_h5_tk")["value"]
    m_h5_tk_enc = driver.get_cookie("_m_h5_tk_enc")["value"]
    thw = driver.get_cookie("thw")["value"]
    tfstk = driver.get_cookie("tfstk")["value"]
    l = driver.get_cookie("l")["value"]
    isg = driver.get_cookie("isg")["value"]
    _uetvid = driver.get_cookie("_uetvid")["value"]
    _ga_YFVFB9JLVB = driver.get_cookie("_ga_YFVFB9JLVB")["value"]
    _ga = driver.get_cookie("_ga")["value"]

    cookie = {
        "thw": thw,
        "_ga_YFVFB9JLVB": _ga_YFVFB9JLVB,
        "_uetvid": _uetvid,
        "_ga": _ga,
        "_m_h5_tk": m_h5_tk,
        "_m_h5_tk_enc": m_h5_tk_enc,
        "tfstk": tfstk.replace("..", "."),
        "l": l.replace("..", "."),
        "isg": isg,
    }

    driver.quit()

    return cookie
