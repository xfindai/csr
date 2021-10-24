"""Jira Retriever

api:
    https://atlassian-python-api.readthedocs.io/jira.html

Querying starting a specific date in Jql:
jql = "type=page and created>2020-05-12"
session.jql(jql, start=0, limit=None, )

pull.yml TEMPLATE:

JiraSource:
  type: Jira
  params:
    credentials:
      username: <USERNAME>
      password: <PASSWORD>
      url: https://<SUBDOMAIN>.jira.com
    projects:
      - Project1
      - Project2

"""

import logging
import requests
from time import time
from datetime import datetime
from atlassian import Jira as _jira


logger = logging.getLogger('main.retriever.Jira')

# Number of items to batch fetch from Jira
BATCH_SIZE = 20

# JQL query for issue id retrieval
INITIAL_REQUEST = (
    "/rest/api/2/search?startAt={start}&maxResults={limit}&expand=names,renderedFields&fields=*all"
    "&jql=project+IN+%28{projects}%29+AND+created%3E%3D{created}+order+by+created"
)


class Jira():
    """Jira
    Retriever
    """

    def __init__(self, source, start_time, ignore_deleted, credentials, projects=None,
                 max_items=None):
        self._logger = logging.getLogger('root')
        self._ignore_deleted = ignore_deleted
        self._start_time = start_time
        self._credentials = credentials
        self._projects = projects or []
        self._max_items = max_items
        self._jira = None
        self._init()

    def _init(self):
        """Initializes required variables"""
        self._jira = _jira(**self._credentials)
        self._session = requests.Session()
        self._session.auth = (self._credentials['username'], self._credentials['password'])

    def get_item_ids(self):
        """Get Item IDs
        Returns empty list as this function is not needed in jira pull process

        Returns:
            yields: empty list
        """
        yield []

    def pre_parse_item(self, item: dict, fields_map: dict) -> dict:
        """Pre parse item
        Translating item's custom fields list to real meaningfull names

        Args:
            item (dict): The item to which fields are translated
            fields_map (dict): The translation map (custom field <-> real name)

        Returns:
            dict: parsed item
        """
        lst = list(item['fields'].keys())
        for k in lst:
            if k in fields_map and 'customfield' in k.lower():
                item['fields'][fields_map[k]] = item['fields'].pop(k)
        return item

    def __iter__(self):
        """Iterator for retrieving items from Jira projects"""

        projects = '%2C'.join(self._projects)
        start_time = self._start_time.strftime('%Y-%m-%d')
        item_index = 0
        while True:

            if self._max_items is not None and item_index >= self._max_items:
                break

            url = self._credentials['url'] + INITIAL_REQUEST.format(
                start=item_index, limit=BATCH_SIZE, created=start_time, projects=projects)

            response = self._get_url_json(url)
            fields_map = response.get('names')

            if not response.get('issues'):
                break

            items_list = []
            for item in response['issues']:
                if fields_map:
                    item = self.pre_parse_item(item, fields_map)
                item['created_at'] = item.get('fields', {}).get('Created', '') or \
                    item.get('fields', {}).get('created', '')
                item['title'] = item.get('fields', {}).get('Summary', '') or \
                    item.get('fields', {}).get('summary', '')
                # TODO: Add proper check for deleted articles!
                item['deleted'] = False
                items_list.append(item)

            yield items_list
            item_index += BATCH_SIZE

    def get_new_fields(self, fields_list: list):
        """Pulls new fields for all existing items"""
        pass


    def _get_url_json(self, url, params=None):
        """Retrieves next Confluence result page"""
        try:
            response = self._session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self._logger.exception('Failed to perform HTTP request: %s', e)
            raise e
