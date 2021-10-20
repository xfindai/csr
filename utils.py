import os
import yaml
import json
import pytz
import dateutil
import datetime
from pathlib import Path
import argparse
import psycopg2
from psycopg2.extras import Json
from collections import defaultdict
from post_actions import FUNCTIONS


def read_yaml(path: Path) -> dict:
    """Reads YAML file
    Returns YAML file as dictionary.

    Arguments:
        path {str} -- Path to YAML file.

    Returns:
        dict -- JSON file loaded as dictionary.
    """
    with open(path, 'r', encoding='utf-8') as fs:
        data = yaml.safe_load(fs)
    return data


def create_argparser() -> argparse.ArgumentParser:
    """Parses and returns command line arguments"""
    # HELP_CONFIG = 'Sources configuration path'
    HELP_STARTTIME = 'Specify from what time to pull data'
    HELP_COMMENT = 'Add a comment to data update record'
    HELP_IGNORE_DEL = 'Ignore deleted items'
    HELP_USERECORD = 'Use existing update record (will use update record start time)'
    HELP_MAXITEMS = 'Number of max items to pull (used for testing)'
    HELP_TEST = 'Test pull on all configurations'
    HELP_UPD_FIELD = 'update specific field'

    parser = argparse.ArgumentParser()

    # parser.add_argument('config', type=str, help=HELP_CONFIG)
    parser.add_argument('-s', '--starttime', type=str, help=HELP_STARTTIME)
    parser.add_argument('-c', '--comment', type=str, default='', help=HELP_COMMENT)
    parser.add_argument('--ignore-deleted', action='store_true', help=HELP_IGNORE_DEL)
    parser.add_argument('--use-record', type=int, help=HELP_USERECORD)
    parser.add_argument('--max-items', type=int, help=HELP_MAXITEMS)
    parser.add_argument('--test', action='store_true', help=HELP_TEST)
    parser.add_argument('-u', '--update-fields', nargs='+', default=[], help=HELP_UPD_FIELD)

    return parser


def get_start_time(start_time: str = None) -> datetime:
    """Get Start Time
    If a data update record exists returns the created_at time after subtraction the default
    overlap time (in minutes) from it. If no data update record exists, returns default start time.

    Arguments:
        start_time (str): From when to pull data (default: None).

    Returns:
        datetime: Start time for pull operation.
    """

    if start_time:
        return dateutil.parser.parse(start_time)

    try:
        file = open('pull_history.txt', 'r')
        date_str = file.readline()
        return dateutil.parser.parse(date_str)
    except Exception:
        pass

    return datetime.datetime.now() - datetime.timedelta(days=1)


def dump_date():
    """Dump date
    dumps the date of the latest successfull pull to file
    """
    try:
        file = open('pull_history.txt', 'w')
        file.write(datetime.datetime.now())
        return True
    except Exception:
        return False


def create_cursor(conn: psycopg2.connect, name: str = "default", itersize: int = 1000):
    """Create cursor
    creates named cursor and sets the itersize
    Args:

    conn (psycopg2.connect): connection for the cursor creation
    name (str): cursor name
    itersize (int, optional): batch size. Defaults to 1000.

    Returns:
        psycopg2.extras.DictCursor: cursor
    """
    cursor = conn.cursor(
        name=name,
        cursor_factory=psycopg2.extras.DictCursor
    )
    cursor.itersize = itersize
    return cursor


def prepare_post_action_field_map(config: list) -> dict:
    result = defaultdict(list)

    for action in config:
        function_name = action.get('function')
        if action.get('apply_to_all'):
            result['_all'].append(function_name)
        else:
            for field in action.get('fields', []) or []:
                result[field].append(function_name)

    return result


def apply_actions_on_field(k: str, v: str, post_action_map: dict) -> str:
    """ apply actions on fields
    applies anonimization function to field value by its key

    Args:
        k (str): jey of the field
        v (str): value if the field
        post_action_map (dict): field to function mapper

    Returns:
        str: altered value
    """
    for func in post_action_map['_all'] + post_action_map.get(k, []) or []:
        v = FUNCTIONS[func](v)

    return v


def apply_post_actions(data: object, key: str = None, post_action_map: dict = None) -> dict:
    """ Apply actions on fields
    Simple recursion which traverses a dictionary and applies functions on the string values

    Args:
        data (object): the root dictionary to traverse
        key (str, optional): Key of the sub dictionary. Defaults to None.
        post_action_map (dict, optional): post action dict which maps fields to functions.

        Returns:
        dict: the altered dictionary
    """

    if isinstance(data, str):
        return apply_actions_on_field(key, data, post_action_map)

    elif isinstance(data, list):
        new_data = []
        for item in data:
            new_data.append(apply_post_actions(item, key, post_action_map))
        return new_data

    elif isinstance(data, dict):
        for k, v in data.items():
            data[k] = apply_post_actions(v, k, post_action_map)
        return data

    return data


def dump_results_to_db(results: str, source: str, cursor):
    """Dump results to DB
    Dumps results batch to DB

    Args:
        results (str): [description]
        source (str): [description]
        cursor ([type]): [description]
    """

    def get_create_at(item):
        created_at = dateutil.parser.parse(item['created_at'])
        if not created_at.tzinfo:
            created_at = pytz.utc.localize(created_at)
        return created_at

    for item in results:

        iid = item.get('id')
        title = item.get('title') or item.get('subject')
        created_at = get_create_at(item)
        deleted = item.get('deleted', False) or False

        data = (source, iid, title, created_at, Json(item), 1, deleted)

        sql = f"INSERT INTO rawitem (source, item_id, title, created_at, json, dataupdate_id, deleted) "\
              f"VALUES (%s, %s, %s, %s, %s, %s, %s)"

        cursor.execute(sql, data)

    cursor.execute('commit')
