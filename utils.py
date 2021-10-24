import os
import yaml
import json
import pytz
import logging
import dateutil
import datetime
from pathlib import Path
import argparse
import psycopg2
from psycopg2.extras import Json
from collections import defaultdict
from actions import FUNCTIONS

LOG = logging.getLogger("root")


def read_yaml(path: Path) -> dict:
    """Reads YAML file
    Returns YAML file as dictionary.

    Arguments:
        path {str} -- Path to YAML file.

    Returns:
        dict -- JSON file loaded as dictionary.
    """
    try:
        with open(path, 'r', encoding='utf-8') as fs:
            data = yaml.safe_load(fs)
        return data
    except Exception as e:
        LOG.error('Could not read yaml file %s', path)
        LOG.debug(e)
        return None


def create_argparser() -> argparse.ArgumentParser:
    """Parses and returns command line arguments"""
    HELP_CONFIG = 'Sources configuration path'
    HELP_STARTTIME = 'Specify from what time to pull data'
    HELP_IGNORE_DEL = 'Ignore deleted items'
    HELP_MAXITEMS = 'Number of max items to pull (used for testing)'
    HELP_UPD_FIELD = 'update specific field'

    parser = argparse.ArgumentParser()

    parser.add_argument('config', type=str, help=HELP_CONFIG)
    parser.add_argument('-s', '--starttime', type=str, help=HELP_STARTTIME)
    parser.add_argument('--ignore-deleted', action='store_true', help=HELP_IGNORE_DEL)
    parser.add_argument('--max-items', type=int, help=HELP_MAXITEMS)
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
    TIME_DELTA_MINS = 15
    try:
        file = open('pull_history.txt', 'w')
        time = datetime.datetime.now() - datetime.timedelta(minutes=TIME_DELTA_MINS)
        file.write(time.strftime("%m/%d/%Y, %H:%M:%S"))
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


def prepare_post_actions_field_map(config: list) -> dict:
    """Preparepost post actions field map
    Constructs a dictionary with fields as keys. The values are lists of functions to be applied
    to the field

    Args:
        config (list): configuration dict

    Returns:
        dict: the post actions field -> key:str - value[callable1, ...]
    """
    field_to_action_map = defaultdict(list)
    actions_config = {}

    for action in config:
        function_name = action.get('function')
        actions_config[function_name] = action
        if action.get('apply_to_all'):
            field_to_action_map['_all'].append(function_name)
        else:
            for field in action.get('fields', []) or []:
                field_to_action_map[field].append(function_name)

    return {'field_to_action_map': field_to_action_map, 'actions_config': actions_config}


def apply_actions_on_field(key: str, value: str, post_action_map: dict) -> str:
    """ apply actions on fields
    applies anonymization function to field value by its key

    Args:
        key (str): jey of the field
        value (str): value if the field
        post_action_map (dict): field to function mapper

    Returns:
        str: altered value
    """
    for action in post_action_map['field_to_action_map']['_all'] + \
            post_action_map['field_to_action_map'].get(key, []) or []:

        # If field is blacklisted, continue to the next action
        if key in post_action_map['actions_config'].get('blacklisted_fields', []) or []:
            continue

        value = FUNCTIONS[action](
            value,
            post_action_map['actions_config'][action].get('blacklisted_patterns', []) or []
        )

    return value


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


def dump_results_to_db(results: list, source_name: str, cursor):
    """Dump results to DB
    Dumps results batch to DB

    Args:
        results (list): List of results
        source_name (str): Source name
        cursor (psycopg2.Cursor): DB connection cursor
    """
    success = failures = 0

    def get_create_at(item):
        """sets the created_at field with the correct UTC timezone"""
        created_at = dateutil.parser.parse(item['created_at'])
        if not created_at.tzinfo:
            created_at = pytz.utc.localize(created_at)
        return created_at

    for item in results:

        iid = item.get('id')
        title = item.get('title') or item.get('subject')
        created_at = get_create_at(item)
        deleted = item.get('deleted', False) or False

        sql = "INSERT INTO rawitem (source, item_id, title, created_at, json, dataupdate_id, "\
              "deleted) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (source, item_id) "\
              "DO UPDATE SET (title, json) = (EXCLUDED.title, EXCLUDED.json)"
        try:
            cursor.execute(sql, (source_name, iid, title, created_at, Json(item), 1, deleted))
            cursor.execute('commit')
            success += 1
        except Exception as e:
            LOG.error('Got error while inserting a line to DB')
            LOG.debug(e)
            failures += 1

    return success, failures


def handle_results_batch(results_batch, source_name: str, post_action_map: dict, cursor):
    """Handle results batch
    handles a bath of results. Applies post actions and dumps to db
    Args:
        results_batch (Iterator): [description]
        source_name (str): [description]
        post_action_map (dict): [description]
        cursor ([type]): [description]

    Returns:
        [type]: [description]
    """
    for result in results_batch:
        result = apply_post_actions(result, None, post_action_map)
    return dump_results_to_db(results_batch, source_name, cursor)
