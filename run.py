from utils import read_yaml, create_argparser, get_start_time, prepare_post_action_field_map, apply_post_actions
from retrievers import RETRIEVERS
import psycopg2
import pprint


CONFIG_FILENAME = 'config.yaml'


def retrieve(config: dict, start_time: dict):
    config = read_yaml('./config.yaml')

    for retriever_config in config['Retrievers']:
        post_action_map = prepare_post_action_field_map(retriever_config['post_retrieval_actions'])
        # if retriever is disabled in config, proceed to the next retriever
        if not retriever_config.get('enabled', False):
            continue

        # get the retriever class
        retriever_class =  RETRIEVERS.get(retriever_config['type'].lower())
        if not retriever_class:
            print(f"Retriever {retriever_config['type']} not found")
            continue

        retriever = retriever_class(source=retriever_config['source_name'],
                                    start_time=start_time,
                                    credentials=retriever_config['credentials'])

        for results_batch in retriever:
            for result in results_batch:
                result = apply_post_actions(result, None, post_action_map)


# def dump_results_to_db(results, cursor):


if __name__ == '__main__':
    options = create_argparser().parse_args()

    config = read_yaml(CONFIG_FILENAME)

    start_time = get_start_time(options.starttime)

    conn = psycopg2.connect(**config['Target'])

    retrieve(config, start_time)
