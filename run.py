import sys
import psycopg2
import logging
import logging.config
from retrievers import RETRIEVERS

from utils import read_yaml, create_argparser, get_start_time, prepare_post_actions_field_map, \
    dump_date, handle_results_batch

LOG = logging.getLogger("root")


# main retrieving loop
def retrieve(config: dict, start_time: dict, cursor):

    # Dumps date of last sussesfull pull
    dump_date()

    for retriever_config in config['Retrievers']:
        total_success = total_failures = 0

        # If retriever is disabled in config, proceed to the next retriever
        if not retriever_config.get('enabled', False):
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
        retriever = retriever_class(source=retriever_config['source_name'],
                                    start_time=start_time, ignore_deleted=True,
                                    **retriever_config['params'])

        # Start iterating over the retrieved batches, and handle them
        for results_batch in retriever:
            success, failures = handle_results_batch(results_batch,
                                                     retriever_config['source_name'],
                                                     post_action_map, cursor)
            total_success += success
            total_failures += failures
            print(f'{total_success=} {total_failures=}', end='\r')

        print()
        LOG.info(
            f"Done pulling {retriever_config['source_name']}. Successfully pulled "
            f"{total_success} items, {total_failures} items failed")


if __name__ == '__main__':
    # Parses runtime arguments and runs retriever

    logging.config.dictConfig(read_yaml('logger_config.yaml'))

    options = create_argparser().parse_args()

    config = read_yaml(options.config)
    if not config:
        LOG.error(f'Could not open configuration file {options.config}')
        sys.exit(1)

    start_time = get_start_time(options.starttime)

    try:
        conn = psycopg2.connect(**config['Target'])
        cursor = conn.cursor()
    except Exception as e:
        LOG.error('Could not establish connection to target database!')
        LOG.debug(e)
        sys.exit(1)

    try:
        retrieve(config, start_time, cursor)
    except Exception as e:
        LOG.error('Pull failed!')
        LOG.debug(e)
        sys.exit(1)
