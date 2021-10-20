from utils import read_yaml, create_argparser, get_start_time, prepare_post_actions_field_map, \
    dump_date, handle_results_batch

from retrievers import RETRIEVERS
import psycopg2
import sys


CONFIG_FILENAME = 'config.yaml'


# main retrieving loop
def retrieve(config: dict, start_time: dict, cursor):

    for retriever_config in config['Retrievers']:
        total_success = total_failures = 0

        # if retriever is disabled in config, proceed to the next retriever
        if not retriever_config.get('enabled', False):
            continue

        print(f"Starting pulling {retriever_config['source_name']}")
        # prepare post actions instructions map
        post_action_map = prepare_post_actions_field_map(retriever_config['post_retrieval_actions'])
        # get the retriever class
        retriever_class = RETRIEVERS.get(retriever_config['type'].lower())

        if not retriever_class:
            print(f"Retriever {retriever_config['type']} not found")
            continue

        retriever = retriever_class(source=retriever_config['source_name'],
                                    start_time=start_time, ignore_deleted=True,
                                    **retriever_config['params'])
        for results_batch in retriever:
            success, failures = handle_results_batch(results_batch,
                                                     retriever_config['source_name'],
                                                     post_action_map, cursor)
            total_success += success
            total_failures += failures
            print(f'{total_success=} {total_failures=}', end='\r')

        print()
        print(
            f"Done pulling {retriever_config['source_name']}. Successfully pulled "\
            f"{total_success} items, {total_failures} items failed")

    # Dumps date of last sussesfull pull
    dump_date()


if __name__ == '__main__':
    # Parses runtime arguments and runs retriever

    options = create_argparser().parse_args()

    config = read_yaml(options.config)
    if not config:
        print(f'could not open configuration file {options.config}')
        sys.exit(0)

    start_time = get_start_time(options.starttime)

    try:
        conn = psycopg2.connect(**config['Target'])
        cursor = conn.cursor()
    except Exception as e:
        print(e)
        sys.exit(0)

    retrieve(config, start_time, cursor)
