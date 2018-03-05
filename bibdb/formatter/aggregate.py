"""Formatters for aggregate data structure."""
from typing import List
from sqlalchemy.orm import with_polymorphic
from .entry import SimpleFormatter
from ..entry.main import Person, Authorship, Editorship, Item, Journal

ORDER_STR = {1: 'st', 2: 'nd', 3: 'rd'}


class AuthoredList(object):
    def __init__(self, session):
        self.ind_formatter = SimpleFormatter()
        self.session = session

    @staticmethod
    def _order_str(order: int) -> str:
        if order % 100 // 10 != 1 and order % 10 in ORDER_STR:
            return str(order) + ORDER_STR[order % 10]
        else:
            return str(order) + 'th'

    def __call__(self, authors: List[Person]) -> str:
        if len(authors) == 0:
            raise ValueError("no author found")
        result_str = list()
        entry = with_polymorphic(Item, '*')
        for author in authors:
            result_str.append(SimpleFormatter.name_filter([author]) + ':')
            authored = self.session.query(entry, Authorship.order).join(Authorship).\
                filter_by(person_id=author.id).all()
            result_str.extend(('\t{0}: as {1} author, {2}'.format(
                x.id, self._order_str(order + 1), self.ind_formatter(x)) for x, order in authored))
            edited = self.session.query(entry).join(Editorship).filter_by(person_id=author.id).all()
            if edited:
                result_str.extend(('\t{0}: as editor, {1}'.format(x.id, self.ind_formatter(x)) for x in edited))
            result_str.append('')
        return '\n'.join(result_str)

