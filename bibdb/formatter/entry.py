import re
from typing import List, Callable, Any, Dict, Type
from io import StringIO
from unicodedata import normalize

from bibtexparser.library import Library
from bibtexparser import write_string
from bibtexparser.model import Entry, Field
from colorama import Fore

from ..entry.main import Item, Person

class Formatter(object):
    def __init__(self, buf):
        self.buf = buf

    @staticmethod
    def name_filter(persons: List[Person], buf) -> None:
        if len(persons) == 0:
            return
        if len(persons) > 1:
            for person in persons[0: -2]:
                buf.write(str.title(person.first_name))
                buf.write(' ')
                buf.write(str.title(person.last_name))
                buf.write(', ')
            person = persons[-2]
            buf.write(str.title(person.first_name))
            buf.write(' ')
            buf.write(str.title(person.last_name))
            buf.write(' & ')
        person = persons[-1]
        buf.write(str.title(person.first_name))
        buf.write(' ')
        buf.write(str.title(person.last_name))

    def __call__(self, entry: Item) -> None:
        raise NotImplementedError

class TitleFormatter(Formatter):
    def __call__(self, entry: Item) -> None:
        buf = self.buf
        buf.write("% ")
        if len(entry.authorship) > 0:
            self.name_filter([x.person for x in entry.authorship], buf)
        if len(entry.editorship) > 0:
            buf.write("\n")
            self.name_filter([x.person for x in entry.editorship], buf)
        buf.write("\n% ")
        buf.write(entry.title)
        buf.write("\n% ")
        buf.write(str(entry.year))
        buf.write("\n\n")

class FileNameFormatter(Formatter):
    file_name_limit = 100
    sanitary_table = dict.fromkeys(list(map(ord, " [:<>*\\?/|'\"{}],.")), None)
    italic = re.compile(r'\\textit{([\w\s]+)}')

    def __call__(self, entry: Item, suffix=''):
        buf = StringIO()
        buf.write(entry.id)
        if len(suffix) > 0:
            buf.write(suffix)
        buf.write(entry.authorship[0].person.last_name)
        buf.write('_')
        buf.write(str(entry.year))
        buf.write('_')
        buf.write(self.italic.sub(r'\1', entry.title.replace(' ', '_')))
        self.buf.write(self.sanitize(buf.getvalue()))

    @staticmethod
    def __shorten_name(string: str) -> str:
        str_list = string.split('_')
        i = 0
        total = 0
        while i < len(str_list):
            total += len(str_list[i])
            i += 1
            if total > FileNameFormatter.file_name_limit:
                break
        return '_'.join(str_list[0:i])

    @staticmethod
    def sanitize(file_name: str) -> str:
        filename = file_name.translate(FileNameFormatter.sanitary_table).replace('-', '_')
        if len(filename) > FileNameFormatter.file_name_limit:
            return FileNameFormatter.__shorten_name(filename)
        else:
            return filename

def get_file_name(entry: Item, suffix: str = '') -> str:
    buf = StringIO()
    return FileNameFormatter.sanitize(FileNameFormatter(buf)(entry, suffix).getvalue())


class SimpleFormatter(Formatter):
    _filters = {'chapter': lambda x: f' Chapter {x}',
                'school': lambda x: f' From {x}',
                'institution': lambda x: f' From {x}',
                'journal': lambda x: x.name}

    def __call__(self, entry: Item) -> None:
        buf = self.buf
        self.name_filter([x.person for x in entry.authorship], buf)
        buf.write(', ')
        if entry.editorship:
            self.name_filter([x.person for x in entry.editorship], buf)
            buf.write(', ')
        for field_id in entry.optional_fields | entry.required_fields - {'id', 'journal_id'} | {'journal'}:
            value = getattr(entry, field_id, None)
            if not value:
                continue
            if field_id == 'number':
                if hasattr(entry, 'volume'):
                    buf.write('(')
                    buf.write(str(value))
                    buf.write(')')
                else:
                    buf.write(' ')
                    buf.write(str(value))
            else:
                _filter = self._filters.get(field_id, None)
                buf.write(_filter(value) if _filter is not None else str(value))
            buf.write(', ')
        buf.write('\n')

class ColorFormatter(SimpleFormatter):
    def __init__(self, buf):
        super(ColorFormatter, self).__init__(buf)
        self._filters['title'] = lambda x: f'{Fore.MAGENTA}{x}{Fore.RESET}'
        self._filters['year'] = lambda x: f'{Fore.RED}{x}{Fore.RESET}'

    @staticmethod
    def name_filter(persons: List[Person], buf, order: int = None) -> None:
        length = len(persons)
        if length == 0:
            return
        second_to_last = length - 2
        last = length - 1
        for idx, author in enumerate(persons):
            if order is not None and idx == order:
                buf.write(Fore.BLUE)
                buf.write(str.title(author.first_name))
                buf.write(' ')
                buf.write(Fore.GREEN)
                buf.write(str.title(author.last_name))
                buf.write(Fore.RESET)
            else:
                buf.write(str.title(author.first_name))
                buf.write(' ')
                buf.write(str.title(author.last_name))
            if idx == second_to_last:
                buf.write(' & ')
            elif idx == last:
                pass
            else:
                buf.write(', ')

    def __call__(self, entry: Item, order: int = None) -> None:
        buf = self.buf
        self.name_filter([x.person for x in entry.authorship], buf, order)
        buf.write(', ')
        if entry.editorship:
            self.name_filter([x.person for x in entry.editorship], buf)
            buf.write(', ')
        for field_id in entry.optional_fields | entry.required_fields - {'id', 'journal_id'} | {'journal'}:
            value = getattr(entry, field_id, None)
            if not value:
                continue
            if field_id == "number":
                if hasattr(entry, "volume"):
                    buf.write('(')
                    buf.write(str(value))
                    buf.write(')')
                else:
                    buf.write(' ')
                    buf.write(str(value))
            else:
                _filter = self._filters.get(field_id, None)
                buf.write(_filter(value) if _filter is not None else str(value))
            buf.write(', ')
        buf.write('\n')

def title_filter(title: str) -> str:
    """escapes capitals because most bibtex systems apply title case"""
    return ' '.join((BibtexFormatter.title_regex.sub(r'{{\1}}', word.strip()) for word in title.split()))

class BibtexFormatter(Formatter):
    title_regex = re.compile(r'^(.+[A-Z].*)$')

    @staticmethod
    def name_filter(persons: List[Person], buf) -> None:
        if len(persons) == 0:
            return
        for person in persons[0: -1]:
            buf.write(str.title(person.last_name))
            buf.write(", ")
            buf.write(str.title(person.first_name))
            buf.write(" and ")
        person = persons[-1]
        buf.write(str.title(person.last_name))
        buf.write(", ")
        buf.write(str.title(person.first_name))

    _filters: Dict[str, Callable[[Any], str]] = {
        'pdf_file': ', '.join,
        'comment_file': ', '.join,
        'keyword': ', '.join,
        'year': str,
        'journal': lambda x: x.name,
        'title': title_filter}

    def __init__(self, buf) -> None:
        super(BibtexFormatter, self).__init__(buf)

    def __call__(self, entry: Item) -> None:
        db = Library()
        entry_dict = dict()
        if len(entry.authorship) > 0:
            buf = StringIO()
            self.name_filter([x.person for x in entry.authorship], buf)
            entry_dict['author'] = buf.getvalue()
        if len(entry.editorship) > 0:
            buf = StringIO()
            self.name_filter([x.person for x in entry.editorship], buf)
            entry_dict['editor'] = buf.getvalue()
        for field_id in entry.optional_fields | entry.required_fields - {'id', 'journal_id'} | {'journal'}:
            value = getattr(entry, field_id, None)
            if value is None:
                continue
            _filter = self._filters.get(field_id, None)
            entry_dict[field_id] = (_filter(value) if _filter is not None else str(value))
        db.add(Entry(
            type(entry).__name__.lower(),
            entry.id,
            [Field(key, value) for key, value in entry_dict.items()]
        ))
        self.buf.write(write_string(db))


class IdFormatter(Formatter):
    @staticmethod
    def name_filter(persons: List[Person], buf) -> None:
        buf.write(''.join(map(lambda x: normalize('NFKD', x)[0], persons[0].last_name.lower().replace(' ', ''))))

    def __call__(self, entry: Item, suffix: str=None) -> None:
        buf = self.buf
        if len(entry.authorship) > 0:
            self.name_filter([x.person for x in entry.authorship], buf)
        elif len(entry.editorship) > 0:
            self.name_filter([x.person for x in entry.editorship], buf)
        else:
            buf.write('anon')
        if hasattr(entry, 'year'):
            buf.write(str(entry.year))
        else:
            buf.write(entry.title.split()[0].title())
        if suffix:
            buf.write(suffix)

def format_once(formatter_class: Type[Formatter], *entry) -> str:
    buf = StringIO()
    formatter = formatter_class(buf)
    formatter(*entry)
    return buf.getvalue()
