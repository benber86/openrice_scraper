import os
import requests
import lxml.html
from lxml.html import HtmlElement
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from enum import Enum
from typing import List, Optional, NamedTuple
from typing_extensions import Literal

HEADER = {"User-Agent": "Mozilla/5.0"}

TITLE_XPATH = '//div[@class="review-title"]'
REVIEW_XPATH = '//section[@class="review-container"]'
SENTIMENT_XPATH = '//div[@class="left-header"]'

RATING_XPATH = '//section[@itemprop="reviewrating"]'
SUBJECT_XPATH = './/div[@class="subject"]'
STAR_XPATH = './/span[@class="or-sprite-inline-block common_yellowstar_desktop"]'

POSITIVE_XPATH = './/div[contains(@class, "smiley_smile")]'
NEUTRAL_XPATH = './/div[contains(@class, "smiley_ok")]'
NEGATIVE_XPATH = './/div[contains(@class, "smiley_cry")]'


class Evaluation(Enum):
    POSITIVE: int = 1
    NEUTRAL: int = 0
    NEGATIVE: int = -1


class Ratings(NamedTuple):

    taste: Optional[int] = None
    environment: Optional[int] = None
    service: Optional[int] = None
    hygiene: Optional[int] = None
    value: Optional[int] = None


class ScrapedData(NamedTuple):
    title: Optional[str] = None
    review: Optional[str] = None
    sentiment: Optional[
        Literal[Evaluation.POSITIVE, Evaluation.NEUTRAL, Evaluation.NEGATIVE]
    ] = None
    taste: Optional[int] = None
    environment: Optional[int] = None
    service: Optional[int] = None
    hygiene: Optional[int] = None
    value: Optional[int] = None


class Scraper:
    def __init__(self, url_file: str) -> None:

        if not os.path.exists(url_file):
            raise OSError("File Not Found: %s" % url_file)

        with open(url_file, "r") as fp:
            self.urls = [_.strip() for _ in fp.readlines()]

        self.data: List[Optional[ScrapedData]] = []

    @staticmethod
    def __requests_retry_session(
        retries: int = 3,
        backoff_factor: float = 0.3,
        status_forcelist: tuple = (500, 502, 504),
        session: Session = None,
    ) -> Session:
        """
        Handles retries for request HTTP requests params are similar to those
        for requests.packages.urllib3.util.retry.Retry
        https://www.peterbe.com/plog/best-practice-with-retries-with-requests
        """
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @staticmethod
    def __safe_extract_text(elements: List[HtmlElement]) -> Optional[str]:
        """
        Returns the text content of the first element extracted from Xpath or None if none has been found
        :param elements:
        The result of a call to .xpath on the tree
        :return: the string extracted or None if there are no elements
        """
        if len(elements) > 0:
            return elements[0].text_content()
        else:
            return None

    @staticmethod
    def __extract_sentiment(
        elements: List[HtmlElement]
    ) -> Optional[
        Literal[Evaluation.POSITIVE, Evaluation.NEUTRAL, Evaluation.NEGATIVE]
    ]:

        if len(elements) < 1:
            return None
        element = elements[0]
        if len(element.xpath(POSITIVE_XPATH)) > 0:
            return Evaluation.POSITIVE
        elif len(element.xpath(NEUTRAL_XPATH)) > 0:
            return Evaluation.NEUTRAL
        elif len(element.xpath(NEGATIVE_XPATH)) > 0:
            return Evaluation.NEGATIVE
        return None

    @staticmethod
    def __extract_ratings(elements) -> Ratings:

        if len(elements) < 1:
            return Ratings()

        element = elements[0]
        rating_subjects = element.xpath(SUBJECT_XPATH)
        if len(rating_subjects) != 5:
            return Ratings()

        extracted_ratings = Ratings(
            *[len(_.xpath(STAR_XPATH)) for _ in rating_subjects]
        )

        return extracted_ratings

    def scrape_page(self, url: str) -> ScrapedData:

        r = self.__requests_retry_session().get(url, headers=HEADER, timeout=10)
        tree = lxml.html.fromstring(r.content)

        # Extract title
        title = self.__safe_extract_text(tree.xpath(TITLE_XPATH))

        # Extract review
        review = self.__safe_extract_text(tree.xpath(REVIEW_XPATH))

        # Extract overall sentiment
        sentiment = self.__extract_sentiment(tree.xpath(SENTIMENT_XPATH))

        # Extract specific grades
        ratings = self.__extract_ratings(tree.xpath(RATING_XPATH))

        return ScrapedData(title, review, sentiment, *ratings._asdict().values())
