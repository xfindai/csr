from utils import read_yaml, create_argparser
from retrievers import retrievers
import psycopg2
import dateutil


def handle(options: dict):
    config = read_yaml('./config.yaml')

    for retriever in config['Retrievers']:

        if not retriever.get('enabled', False):
            continue

        if func := retrievers.get(retriever['type']):
            func(retriever)

        print(retriever['type'])


if __name__ == '__main__':
    args = create_argparser().parse_args()
    print(args)
    config = read_yaml('./config.yaml')
    
    if args['starttime']:
        start_time = 
    
    conn = psycopg2.connect(**config['Target'])

