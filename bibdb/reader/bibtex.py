import re
from calendar import month_abbr, month_name
from typing import Set, List, Tuple, Union, Dict

import bibtexparser

from .main import Reader

month_index = {name.lower(): number for number, name in enumerate(month_name)}
month_index.update({name.lower(): number for number, name in enumerate(month_abbr)})
quotations = {"'": "'", '(': ")", "{": "}", '"': '"'}
title_regex = re.compile('<\s*i\s*>([\w\s]+)<\s*/i>')
pages_regex = re.compile('^(\w*)(\d+)[-:_]{1,2}(\d+)$')


def __filter_common(item_str: str) -> str:
    item_str = item_str.strip(',')
    while True:
        if item_str[0] in quotations:
            if item_str[-1] == quotations[item_str[0]]:
                item_str = item_str[1:-1]
                continue
        break
    return item_str


def __filter_people(people: str) -> List[Tuple[str, str]]:
    """split people string
    Args:
        people: Last_name, F.N. and Last_name2, F.N2 and Last_name3, F.N3
    Returns:
        list of (last_name, first_middle_name)
    """
    people = people.replace('\n', ' ').split(' and ')
    return [__filter_name(x) for x in people if not x.startswith('other')]


def __filter_name(name: str) -> Union[None, Tuple[str, str]]:
    """Make people names as surname, first and middle names
    Returns:
        [last_name, first_middle_name]
    """
    name = name.strip()
    if len(name) < 1:
        return None
    if ',' in name:
        name_split = name.split(',', 1)
        last = name_split[0].strip()
        firsts = [i.strip() for i in name_split[1].split()]
    else:
        name_split = name.split()
        last = name_split.pop()
        firsts = [i.replace('.', '. ').strip() for i in name_split]
    if last in ['jnr', 'jr', 'junior']:
        last = firsts.pop()
    for item in firsts:
        if item in ['ben', 'van', 'der', 'de', 'la', 'le']:
            last = firsts.pop() + ' ' + last
    return last.lower(), ' '.join(firsts).lower()


def __filter_pages(pages: str) -> str:
    """force pages formatting 123-126, 123-6, 123:126, 123--126, 123_126 to 123-126"""
    if '.' in pages or '/' in pages:  # don't change pages in the form xx.xxx/xx.xxx
        return pages
    result = pages_regex.match(pages)
    if not result:
        return pages
    page_start, page_end = result.group(2), result.group(3)
    if len(page_end) < len(page_start):  # add back truncated end page digits
        page_end = page_start[0:len(page_start) - len(page_end)] + page_end
    return '{0}{1}-{2}'.format(result.group(1), page_start, page_end)


def __filter_file(file: str) -> List[str]:
    return [name.strip() for name in file.split(', ')]


__filter_dict = {
    'type': str.lower,
    'author': __filter_people,
    'editor': __filter_people,
    'pages': __filter_pages,
    'month': lambda x: int(month_index[x.lower()]) if x.lower() in month_index else int(x),
    'pdf_file': __filter_file,
    'comment_file': __filter_file,
    'keyword': lambda x: {y.strip().lower() for y in x.split(',')},
    'title': lambda x: title_regex.sub(r'\\textit{\1}', x),
    'journal': lambda x: x[4:] if x.startswith("The ") or x.startswith("the ") else x}


def __custom_filter(entry: Dict[str, Union[str, int]]) -> Dict[str, Union[str, int, List, Set]]:
    entry = bibtexparser.customization.convert_to_unicode(entry)
    for key in entry:
        item = __filter_common(entry[key])
        if key in __filter_dict:
            item = __filter_dict[key](item)
        # noinspection PyBroadException,PyBroadException
        try:
            item = int(item)
        except (ValueError, TypeError):
            pass
        entry[key] = item
    return entry


_parser = bibtexparser.bparser.BibTexParser()
_parser.customization = __custom_filter


class BibtexReader(Reader):
    # noinspection PyMissingConstructor
    def __init__(self, fp):
        self.fp = fp

    def __call__(self):
        return bibtexparser.load(self.fp, parser=_parser)
