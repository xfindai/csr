from utils import read_yaml
from retrievers import retrievers

config = read_yaml('./config.yaml')
log = []

for retriever in config['Retrievers']:

    if not retriever.get('enabled', False):
        continue

    if func := retrievers.get(retriever['type']):
        func(retriever)

    print(retriever['type'])

