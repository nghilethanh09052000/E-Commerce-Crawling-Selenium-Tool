from time import time

from navee_logging.logger import NaveeLogger
from navee_logging.enums import NaveeModule


def test():
    logger = NaveeLogger(NaveeModule.ARCHIVING_WORKER, "a", "a", "eu-west-1")

    logger.input(
        "Test message",
        call_name="test call",
        post_id=3,
        domain_name="facebook.com",
    )


if __name__ == "__main__":
    test()
