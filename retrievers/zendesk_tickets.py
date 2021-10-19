"""
Zendesk Tickets Retriever

pull.yml TEMPLATE:

ZendeskSource:
  type: ZendeskTickets
  params:
    credentials:
      email: <USERNANE>
      token: <TOKEN>
      subdomain: d3v-xfind

"""
import os
import json
import logging
from datetime import datetime
from zenpy import Zenpy
from typing import Generator


logger = logging.getLogger('main')


COMMENT_FIELDS = ["author_id", "body", "id", "public", "type", "created_at"]


class ZendeskTickets():
    """Zendesk Tickets
    Retriever
    """

    def __init__(self, source: str, start_time: datetime, ignore_deleted: bool = True,
                 credentials: dict = {}, max_items: int = None):
        #super().__init__(source, update_record, ignore_deleted)
        self._ignore_deleted = ignore_deleted
        self._start_time = start_time
        self._credentials = credentials
        self._max_items = max_items
        self._client = None
        self._init()

    def _init(self):
        """Initializes required variables/objects"""
        # Should be either:
        # {email: email, token: token, subdomain: subdomain} OR
        # {email: email, password: password, subdomain: subdomain}
        self._client = Zenpy(**self._credentials)

    def get_item_ids(self) -> Generator:
        """Get Item IDs
        Doesn't support using database for pulling by item id.

        Returns:
            yields: List of item IDs.
        """
        if False:
            yield []

    def __iter__(self):
        """Iterator for retrieving items from Zendesk"""

        # Retrieves ticket custom fields:
        ticket_fields = self._get_ticket_fields()
        tickets = self._client.tickets.incremental(start_time=self._start_time.strftime('%s'))

        for i, ticket in enumerate(tickets):

            # Stop if reached max items:
            if self._max_items is not None and i >= self._max_items:
                break

            if self._ignore_deleted and ticket.status == 'deleted':
                continue

            tmp = self._get_ticket_attributes(ticket)
            tmp = self._get_custom_fields(tmp, ticket_fields)
            tmp['comments'] = self._get_ticket_comments(ticket.id)

            # Checks if deleted:
            tmp['deleted'] = (ticket.status == 'deleted')

            yield [tmp]

    def get_new_fields(self, fields_list: list):
        """Pulls new fields for all existing items"""
        pass

    def _get_ticket_fields(self):
        """Get Ticket Fields
        Retrieves all ticket fields from Zendesk API into a dictionary by IDs.

        Returns:
            dict -- Fields dictionary.
        """
        tfields = {}
        ticket_fields = self._client.ticket_fields()
        for field in ticket_fields:
            tfields[field.id] = field.to_dict()
        return tfields

    def _get_ticket_comments(self, ticket_id):
        """Get Ticket Comment
        Retrieves all comments for the specified ticket.

        Arguments:
            ticket_id {int} -- ID of the ticket we want to get the comment for.

        Returns:
            list of dict -- List of dictionaries representing comments.
        """
        comments = []
        try:
            for comment in self._client.tickets.comments(ticket=ticket_id):
                comment_data = {}
                for field in COMMENT_FIELDS:
                    comment_data[field] = getattr(comment, field)
                comments.append(comment_data)
        except Exception:
            # logger.warning("No comments?")
            pass
        return comments

    @staticmethod
    def _get_ticket_attributes(obj):
        """Get Ticket Attributes
        Pulls ticket data into dictionary including all attributes that contain to_dict method.

        Arguments:
            obj {Zenpy.Ticket} -- Ticket object.

        Returns:
            dict -- Ticket as a dictionary.
        """
        ticket = {}
        for attr in [a for a in dir(obj) if not a.startswith('_')]:
            try:
                value = getattr(obj, attr, None)
                todict = getattr(value, 'to_dict', None)
                ticket[attr] = todict() if todict else value
            except Exception:
                ticket[attr] = "xFind: Error retrieving object"
        ticket = json.loads(json.dumps(ticket, default=str))
        return ticket

    @staticmethod
    def _get_custom_fields(ticket, tfields):
        """Get Custom Fields
        Adds information for ticket fields API to ticket fields attribute.

        Arguments:
            ticket {dict} -- Dictionary of a ticket data.
            tfields {dict} -- Dictionary of ticket fields with their ID as key.

        Returns:
            dict -- Updated ticket dictionary.
        """
        custom_fields = ['custom_fields', 'fields']
        fields_to_add = ['title', 'description', 'required', 'type']
        for cfield in custom_fields:
            fields = ticket[cfield]
            for field in fields:
                # We put an if here since we had cases where the id in field['id']
                # was not in tfields.
                if field['id'] in tfields:
                    field['xdata'] = {
                        k: v for k, v in tfields[field['id']].items() if k in fields_to_add}
        return ticket
