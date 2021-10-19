import yaml
import dateutil
import datetime
from pathlib import Path
import argparse


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
    else:
        return datetime.datetime.now() - datetime.timedelta(days=1)
