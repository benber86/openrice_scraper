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
WWW = 'www'
RESTAURANT_FINGERPRINTS = ['hongkong/r-', 'restaurants']
REVIEW_FINGERPRINT = 'review/'
REVIEW_FILE = 'reviewsurl.csv'

class Crawler:

    def __init__(self, start_url: str = None, language='zh', timeout=10) -> None:
        self.start_url = start_url
        self.language = language
        self.timeout = timeout
        self.history = set()
        self.reviews = set()

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
        try:
            r = self.__requests_retry_session().get(url, headers=HEADER, timeout=10)
        except Exception as e:
            print("Exception : %s" % e)
            
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
                if link[0] != '/' and domain_info.domain != DOMAIN_NAME:
                    continue

                if link[0] == '/':
                    link = DOMAIN_PREFIX + link

                extracted_links.append(link)

        return extracted_links

    def _filter_restaurant_and_review_links(self, links: List[str]) -> (List[str], List[str]):
        """
        Filters a list of links to extract links to restaurant info and links to reviews
        :param links: a list of links
        :return: a tuple containing a list of restaurant links and review links
        """

        links = [l for l in links if tldextract.extract(l).subdomain == WWW and ('/%s/' % self.language) in l]

        review_links = [l for l in links if REVIEW_FINGERPRINT in l and l not in self.reviews]
        restaurant_links = []

        for fingerprint in RESTAURANT_FINGERPRINTS:
            for link in links:
                if fingerprint in link and link not in self.history:
                    restaurant_links.append(link)

        restaurant_links = list(set(restaurant_links))
        review_links = list(set(review_links))

        return restaurant_links, review_links

    def __save_review_links(self) -> None:

        with open(REVIEW_FILE, 'w') as fp:
            fp.write('\n'.join(self.reviews))

    def crawl(self, url: str, recur_level: int=0) -> None:
        """
        Main crawling function
        :param url: url to start the crawl from
        :param recur_level: max recursion level to prevent crawling endlessly
        :return:
        """

        if recur_level > 25 or url in self.history:
            return

        print("Crawling: %s\nRecursion level: %s" % (url, recur_level))
        links_extracted = self.extract_internal_links(url)
        restaurant_links, review_links = self._filter_restaurant_and_review_links(links_extracted)
        self.reviews.union(review_links)
        self.history.add(url)

        if not (len(self.history) % 1000):
            print("="*25)
            print("Total pages crawled: %s" % len(self.history))
            print("Total reviews collected: %s" % len(self.reviews))
            print("Saving...")
            self.__save_review_links()

        for link in restaurant_links:
            self.crawl(link, recur_level+1)


if __name__ == '__main__':
    c = Crawler()
    e = c.crawl('https://www.openrice.com/en/hongkong/r-micasadeco-cafe-hong-kong-mong-kok-western-dessert-r643135/reviews')