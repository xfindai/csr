

from .zendesk_articles import ZendeskArticles
from .zendesk_tickets import ZendeskTickets

ALL = [
    ZendeskArticles, ZendeskTickets
]

# Integration name to retriever map
RETRIEVERS = {r.__name__.lower(): r for r in ALL}


