import lxml.html
from typing import List
import requests
import tldextract
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

DOMAIN_PREFIX = 'https://www.openrice.com'
DOMAIN_NAME = 'openrice'
HEADER = {'User-Agent': 'Mozilla/5.0'}


class Crawler:

    def __init__(self, start_url: str = None) -> None:
        self.start_url = start_url
        self.history = {}

    @staticmethod
    def __requests_retry_session(
            retries: int = 3,
            backoff_factor: float = 0.3,
            status_forcelist: tuple = (500, 502, 504),
            session: Session = None,
    ) -> Session:
        """
        Handles retries for request HTTP requests
        params are similar to those for requests.packages.urllib3.util.retry.Retry
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
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def extract_internal_links(self, url: str = None) -> List[str]:
        """
        Extract all the links pointing to the same domain on a page
        from its url
        :param url: URL of the page
        :return: List of links as strings
        """

        extracted_links = []
        r = self.__requests_retry_session().get(url, headers=HEADER)
        tree = lxml.html.fromstring(r.content)

        body = tree.find('body')
        if body is not None:
            a_elements = body.xpath('.//a')
        else:
            a_elements = tree.xpath('.//a')

        if a_elements is None:
            return []

        for element in a_elements:

            link = element.get('href')
            if link is not None and len(link) > 0:
                link = link.strip()

                domain_info = tldextract.extract(link)
                if (link[0] != '/' and domain_info.domain != DOMAIN_NAME):
                    continue

                if link[0] == '/':
                    link = DOMAIN_PREFIX + link

                extracted_links.append(link)

        return extracted_links



if __name__ == '__main__':
    c = Crawler()
    c.extract_internal_links('https://www.openrice.com/en/hongkong/r-micasadeco-cafe-hong-kong-mong-kok-western-dessert-r643135/reviews')