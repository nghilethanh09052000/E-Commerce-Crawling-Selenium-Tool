import json
import time
import traceback
from itertools import cycle
from xml.sax.saxutils import unescape

import timeout_decorator
from selenium import webdriver

from eb_infex_worker.information_extraction.pattern_detection.pattern_detector import PatternDetector
from eb_infex_worker.information_extraction.pattern_detection.utils import is_driver_live


class PatternTester:
    def __init__(self, test_pages):

        self.patternDetector = PatternDetector()

        self.__update_drivers()

        self.test_pages = test_pages
        self.test_idx = 0
        self.actions_iterator = cycle((self.__load_next_page, self.__run_pattern_detection))

    def __enter__(self):

        return self

    def __exit__(self, exc_type, exc_value, tb):

        self.__update_drivers()
        self.driver_pages.close()
        self.driver_images.close()

    def __update_drivers(self):

        # Check if the attribute driver_pages has not already been defined or if it is dead
        if not hasattr(self, "driver_pages") or not is_driver_live(self.driver_pages):
            self.driver_pages = webdriver.Chrome()

        # Check if the attribute driver_images has not already been defined or if it is dead
        if not hasattr(self, "driver_images") or not is_driver_live(self.driver_images):
            self.driver_images = webdriver.Chrome()

    @timeout_decorator.timeout(120)
    def __load_page_and_image(self):
        self.driver_pages.get(self.page_url)
        self.driver_images.get(self.image_url)

    def __get_html(self):

        self.html = unescape(self.driver_pages.page_source)

    def __load_next_page(self):

        if self.test_idx >= len(test_pages):
            print("Exiting because you have iterated through all the test pages")
            exit()

        print(f"\n{self.test_idx}.")

        self.page_url, self.image_url, self.s3_url = test_pages[self.test_idx]
        self.test_idx += 1

        self.__update_drivers()

        self.__load_page_and_image()

        # Some pages really finish loading (JS) after the end of the get() (when the loading arrow stops spinning)
        time.sleep(1)

        # In case of a redirection
        self.page_url = self.driver_pages.current_url

        self.__get_html()

    def __run_pattern_detection(self):

        start = time.time()

        self.patternDetector.search_pattern(self.html, self.page_url, self.image_url, self.s3_url)

        print(f"\nsearch_pattern ran in {round(time.time() - start, 3)} seconds")

    def nextAction(self):

        try:
            # next(self.actions_iterator)()
            self.__load_next_page()
            self.__run_pattern_detection()
        except Exception as e:
            print(traceback.print_tb(e.__traceback__))
            print(e)

            return


if __name__ == "__main__":

    with open("../../Downloads/pattern_detection_test_rise.json", "r") as f:
        test_pages = json.load(f)

    with PatternTester(test_pages) as patternTester:

        while True:
            input("\nPress Enter to continue...\n")
            patternTester.nextAction()
