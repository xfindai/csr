"""
Zendesk Articles Retriever

pull.yml TEMPLATE:

ArticleSource:
  type: ZendeskArticles
  params:
    subdomain: xfind
    credentials:
      username: <USERNAME>
      password: <PASSWORD>

"""
import time
import logging
import requests

from datetime import datetime
from utils import set_deleted

logger = logging.getLogger('main')
DEF_SOURCE = 'ArticleSource'


class ZendeskArticles():
    """Zendesk Articles
    Retriever
    """

    # ARTICLES_API = 'https://{}.zendesk.com/api/v2/help_center/incremental/articles.json?{}'
    ARTICLES_API = 'https://{}.zendesk.com/api/v2/help_center/{}/articles.json?{}'
    CATEGORIES_API = 'https://{}.zendesk.com/api/v2/help_center/categories.json'
    SECTIONS_API = 'https://{}.zendesk.com/api/v2/help_center/sections.json'

    def __init__(self, source: str, start_time: datetime, ignore_deleted: bool,
                 subdomain: str, locale: str, credentials: dict, max_items: int = None):
        self._ignore_deleted = ignore_deleted
        self._start_time = start_time
        self._subdomain = subdomain
        self._source = source
        self._locale = locale or 'en-us'
        self._credentials = credentials
        self._max_items = max_items
        self._url = None
        self._session = None
        self._page_count = 0
        self._total = 0
        self._items: list = []
        self._init()

    def _init(self):
        """Initializes required variables"""
        attrs = f"start_time={self._start_time.strftime('%s')}"
        self._url = self.ARTICLES_API.format(self._subdomain, self._locale, attrs)
        logger.info("Using API URL: '%s'", self._url)
        self._session = requests.Session()
        self._session.auth = (self._credentials['username'], self._credentials['password'])

    def get_item_ids(self) -> list:
        """Get Item IDs
        Doesn't support using database for pulling by item id.

        Returns:
            yields: List of item IDs.
        """
        yield []

    def __iter__(self):
        return self

    def __next__(self):
        """Iterator for retrieving items from Zendesk"""
        if not self._url:
            self._sync_deleted()
            raise StopIteration

        # Stop if reached max items:
        if self._max_items is not None and self._total >= self._max_items:
            self._sync_deleted()
            raise StopIteration

        # Retrieves page from zendesk api:
        response = self._session.get(self._url)
        if response.status_code != 200:
            print('Failed to retrieve articles with error {}'.format(response.status_code))
            exit()

        data = response.json()
        # Retrieves sections for breadcrumbs:
        sections = self._get_breadcrumbs()
        self._items = data.get('articles', [])
        self._total += len(self._items)
        for item in self._items:
            item['breadcrumbs'] = sections[item['section_id']]
            item['deleted'] = False

        self._url = data.get('next_page')
        return self._items

    def get_new_fields(self, fields_list: list):
        """Pulls new fields for all existing items"""
        pass

    def _get_breadcrumbs(self):
        """Get Sections
        Retrieves breadcrumbs for articles using retrieved sections.

        Returns:
            dict: Section IDs as keys and breadcrumbs as values.
        """
        categories = self._get_categories()
        logger.debug('Retrieving sections...')
        url = self.SECTIONS_API.format(self._subdomain)
        sections = []
        while url:
            response = self._get_page_from_url(url)
            data = response.json()
            sections.extend(data.get('sections', []))
            url = data.get('next_page')
        sections = {x["id"]: f"{categories[x['category_id']]} > {x['name']}" for x in sections}
        logger.debug('Retrieved categories:\n%s', sections)
        return sections

    def _get_categories(self):
        """Get categories.
        this is the breadcrumbs path

        Args:
            session (requests.Session): Session object.
            subdomain (str): Company's Zendesk subdomain.

        Returns:
            dict: of ids to categeries name.
        """
        logger.debug('Retrieving categories...')
        url = self.CATEGORIES_API.format(self._subdomain)
        categories = []
        while url:
            response = self._get_page_from_url(url)
            data = response.json()
            categories.extend(data.get('categories', []))
            url = data.get('next_page')
        categories = {x["id"]: x["name"] for x in categories}
        logger.debug('Retrieved categories:\n%s', categories)
        return categories

    def _get_page_from_url(self, url):
        """Returns next items page from API"""
        logger.debug('Fetching page %s', url)
        response = None
        while url:
            response = self._session.get(url)
            if response.status_code == 200:
                break

            if response.status_code != 429:
                logger.warn("Received status code %s (not 200 or 429):\n%s",
                            response.status_code, response)
                print(response.__dict__)
            # if response.status_code != 429:
            #     break
            # Retry in case of blocked
            logger.debug('Had to sleep for %s', response.headers.get('retry-after', None))
            time.sleep(int(response.headers.get('retry-after', 1)))
        return response

    def _sync_deleted(self):
        """Sync Deleted
        Filters all articles that are not in the _all_article_ids set and sets their
        deleted attribute to True.
        """
        logger.info("Retrieving deleted articles...")
        start_time = datetime(2019, 1, 1)
        attrs = f"start_time={start_time.strftime('%s')}"
        url = self.ARTICLES_API.format(self._subdomain, self._locale, attrs)

        articles = []
        while url:
            response = self._get_page_from_url(url)
            data = response.json()
            # Also removes draft articles
            articles.extend(a['id'] for a in data.get('articles', []) if not a['draft'])
            url = data.get('next_page')

        # Takes all articles and excludes articles in the _all_article_ids set and sets these
        # to deleted=True:
        set_deleted(articles, self._source)
