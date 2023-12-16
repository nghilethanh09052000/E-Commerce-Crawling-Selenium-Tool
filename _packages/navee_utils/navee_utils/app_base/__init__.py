"""This module is a compilation of functions that need to be run at the start of the program."""

import os
import time


def start():
    set_timezone()


def set_timezone():
    os.environ["TZ"] = "UTC"
    time.tzset()


start()
