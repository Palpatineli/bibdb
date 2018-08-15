"""Formatters for aggregate data structure."""
from typing import List
from io import StringIO
from .entry import ColorFormatter
from ..entry.main import Item

ORDER_STR = {1: 'st', 2: 'nd', 3: 'rd'}


class AuthoredList(object):
    def __init__(self):
        self.ind_formatter = ColorFormatter()

    @staticmethod
    def _order_str(order: int) -> str:
        if order % 100 // 10 != 1 and order % 10 in ORDER_STR:
            return str(order) + ORDER_STR[order % 10]
        else:
            return str(order) + 'th'

    def __call__(self, entries: List[Item]) -> str:
        result: StringIO = StringIO()
        for x, order in entries:
            result.write(self.ind_formatter(x, order))
            result.write("\n")
        return result.getvalue()
