from typing import List

from .entry import SimpleFormatter
from ..entry.main import Person

ORDER_STR = {1: 'st', 2: 'nd', 3: 'rd'}


class AuthoredList(object):
    ind_formatter = SimpleFormatter()

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
        for author in authors:
            result_str.append(SimpleFormatter.name_filter([author]) + ':')
            authored = sorted(author.authorship, key=lambda x: (x.item.year, x.order + 1))
            result_str.extend(('\t{0.id}: as {1} author, {2}'.format(
                x.item, self._order_str(x.order), self.ind_formatter(x.item)) for x in authored))
            edited = sorted([(x.item.year, x.order + 1, x.item) for x in author.editorship])
            result_str.extend(('\t{0.id}: as {1} editor, {2}'.format(
                x[2], self._order_str(x[1]), self.ind_formatter(x[2])) for x in edited))
            result_str.append('')
        return '\n'.join(result_str)
