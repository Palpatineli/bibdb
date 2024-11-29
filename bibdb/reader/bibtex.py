import re
from typing import List, Tuple, Union

import bibtexparser
from bibtexparser import middlewares as m
from bibtexparser.middlewares.middleware import Library, Block, Entry

from .main import Reader


class RemoveMoreEnclosingMiddleware(m.RemoveEnclosingMiddleware):
    quotations = {"'": "'", '(': ")", "{": "}", '"': '"'}

    @staticmethod
    def _strip_enclosing(value: str) -> Tuple[str, str]:
        item_str = value.strip(',')
        if len(item_str) == 0:
            return item_str, "no-enclosing"
        enclosing = []
        while item_str[0] in RemoveMoreEnclosingMiddleware.quotations and\
            item_str[-1] == RemoveMoreEnclosingMiddleware.quotations[item_str[0]]:
            enclosing.append(item_str[0])
            item_str = item_str[1:-1]
        return item_str, "no-enclosing" if len(enclosing) == 0 else "".join(enclosing)



class PageParser(m.BlockMiddleware):
    pages_regex = re.compile('^(\w*)(\d+)[-:_]{1,2}(\d+)$')

    @staticmethod
    def _filter_pages(pages: str) -> str:
        """force pages formatting 123-126, 123-6, 123:126, 123--126, 123_126 to 123-126"""
        if '.' in pages or '/' in pages:  # don't change pages in the form xx.xxx/xx.xxx
            return pages
        result = PageParser.pages_regex.match(pages)
        if not result:
            return pages
        page_start, page_end = result.group(2), result.group(3)
        if len(page_end) < len(page_start):  # add back truncated end page digits
            page_end = page_start[0:len(page_start) - len(page_end)] + page_end
        return '{0}{1}-{2}'.format(result.group(1), page_start, page_end)

    def transform_entry(self, entry: Entry, library: Library) -> Union[Block, None]:
        val = entry.get('pages')
        if val is not None:
            entry['pages'] = self._filter_pages(val.value)
        return entry


class FileParser(m.BlockMiddleware):
    @staticmethod
    def _filter_file(file: str) -> List[str]:
        return [name.strip() for name in file.split(', ')]

    def transform_entry(self, entry: Entry, library: Library) -> Union[Block, None]:
        for field in ('pdf_file', 'comment_file'):
            val = entry.get(field)
            if val is not None:
                entry[field] = self._filter_file(val.value)
        return entry


class MiscParser(m.BlockMiddleware):
    title_regex = re.compile('<\s*i\s*>([\w\s]+)<\s*/i>')

    def transform_entry(self, entry: Entry, library: Library) -> Union[Block, None]:
        val = entry.get('keyword')
        if val is not None:
            entry['keyword'] = {y.strip().lower() for y in val.value.split(',')}
        val = entry.get('title')
        if val is not None:
            entry['title'] = self.title_regex.sub(r'\\textit{\1}', val.value)
        val = entry.get('journal')
        if val is not None:
            entry['journal'] = val.value.lstrip('The ').lstrip('the ')
        return entry


class BibtexReader(Reader):
    layers = [
        RemoveMoreEnclosingMiddleware(),
        m.MonthIntMiddleware(),
        m.SeparateCoAuthors(),
        m.SplitNameParts(),
    ]

    # noinspection PyMissingConstructor
    def __init__(self, text: str):
        self.text = text

    def __call__(self):
        return bibtexparser.parse_string(self.text, append_middleware=self.layers)
