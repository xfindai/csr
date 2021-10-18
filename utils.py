import yaml
from pathlib import Path


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
