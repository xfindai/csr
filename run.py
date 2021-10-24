import sys
import psycopg2
import argparse
import logging
import logging.config
from retrievers import RETRIEVERS

from utils import read_yaml, get_start_time, prepare_post_actions_field_map, \
    dump_date, handle_results_batch

LOGGER_CONFIG_FILE_NAME = 'logger_config.yaml'
logging.config.dictConfig(read_yaml(LOGGER_CONFIG_FILE_NAME))
LOG = logging.getLogger("root")
EXIT_CODE_ON_ERR = 1


# main retrieving loop
def retrieve(config: dict, start_time: dict, cursor):

    # Dumps date of last sussesfull pull
    dump_date()

    for retriever_config in config['Retrievers']:
        total_success = total_failures = 0

        # If retriever is disabled in config, proceed to the next retriever
        if not retriever_config.get('enabled', False):
            LOG.info(f"Skipping {retriever_config['source_name']} as it is disabled in config")
            continue

        LOG.info(f"Starting pulling {retriever_config['source_name']}")
        # Prepare post actions instructions map
        post_action_map = prepare_post_actions_field_map(retriever_config['post_retrieval_actions'])
        # Get the retriever class
        retriever_class = RETRIEVERS.get(retriever_config['type'].lower())
        # No retriever was found, proceed to the next source
        if not retriever_class:
            LOG.warning(f"Retriever {retriever_config['type']} not found")
            continue

        # Initiate the retriever with config params
        retriever = retriever_class(source=retriever_config['source_name'], start_time=start_time,
                                    ignore_deleted=True, **retriever_config['params'])

        # Start iterating over the retrieved batches, and handle them
        for results_batch in retriever:
            success, failures = handle_results_batch(results_batch, retriever_config['source_name'],
                                                     post_action_map, cursor)
            total_success += success
            total_failures += failures
            print(f'{total_success=} {total_failures=}', end='\r')

        print()
        LOG.info(
            f"Done pulling {retriever_config['source_name']}. Successfully pulled "
            f"{total_success} items, {total_failures} items failed")


def create_argparser() -> argparse.ArgumentParser:
    """Parses and returns command line arguments"""
    HELP_CONFIG = 'Sources configuration path'
    HELP_STARTTIME = 'Specify from what time to pull data'
    HELP_MAXITEMS = 'Number of max items to pull (used for testing)'

    parser = argparse.ArgumentParser()

    parser.add_argument('config', type=str, help=HELP_CONFIG)
    parser.add_argument('-s', '--starttime', type=str, help=HELP_STARTTIME)
    parser.add_argument('--max-items', type=int, help=HELP_MAXITEMS)

    return parser


if __name__ == '__main__':
    # Parses runtime arguments and runs retriever

    options = create_argparser().parse_args()

    config = read_yaml(options.config)
    if not config:
        LOG.error(f'Could not open configuration file {options.config}')
        sys.exit(EXIT_CODE_ON_ERR)

    start_time = get_start_time(options.starttime)

    try:
        conn = psycopg2.connect(**config['Target'])
        cursor = conn.cursor()
    except Exception as e:
        LOG.error('Could not establish connection to target database!')
        LOG.debug(e)
        sys.exit(EXIT_CODE_ON_ERR)

    try:
        retrieve(config, start_time, cursor)
    except Exception as e:
        LOG.error('Pull failed!')
        LOG.debug(e)
        sys.exit(EXIT_CODE_ON_ERR)
