from typing import List
import re
from unicodedata import normalize
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter
from ..entry.main import Item, Person


class Formatter(object):
    @staticmethod
    def name_filter(persons: List[Person]) -> str:
        if len(persons) > 1:
            return (persons[0].last_name + '_' + persons[1].last_name).replace(' ', '')
        else:
            return persons[0].last_name.replace(' ', '')

    def __call__(self, entry: Item):
        raise NotImplementedError


class TitleFormatter(Formatter):
    @staticmethod
    def name_filter(persons: List[Person]) -> str:
        if len(persons) == 0:
            return ''
        author_list = [str.title('{0.first_name} {0.last_name}'.format(author)) for author in persons]
        if len(author_list) > 1:
            return '% {0} & {1}\n'.format(', '.join(author_list[0:-1]), author_list[-1])
        else:
            return '% ' + author_list[0]

    def __call__(self, entry: Item):
        str_list = [self.name_filter([x.person for x in entry.authorship]) if len(entry.authorship) > 0 else '',
                    self.name_filter([x.person for x in entry.editorship]) if len(entry.editorship) > 0 else '',
                    '% {0.title}\n% {0.year}\n\n']
        return ''.join(str_list).format(entry)


class FileNameFormatter(Formatter):
    file_name_limit = 100
    sanitary_table = dict.fromkeys(list(map(ord, " [:<>*\\?/|'\"{}],.")), None)
    italic = re.compile(r'\\textit{([\w\s]+)}')

    def __call__(self, entry: Item, suffix=''):
        str_list = [entry.id]
        if len(suffix) > 0:
            str_list.append(suffix)
        str_list.extend([self.name_filter([x.person for x in entry.authorship]), entry.year,
                         self.italic.sub(r'\1', entry.title.replace(' ', '_'))])
        return self._sanitize('_'.join(str_list))

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
    def _sanitize(file_name: str) -> str:
        filename = file_name.translate(FileNameFormatter.sanitary_table).replace('-', '_')
        if len(filename) > FileNameFormatter.file_name_limit:
            filename = FileNameFormatter.__shorten_name(filename)
        return filename


_field_ids = ['year', 'title', 'journal', 'booktitle', 'chapter', 'pages', 'publisher', 'school',
              'institution', 'address', 'note']


class SimpleFormatter(Formatter):
    filters = {'chapter': lambda x: ' Chapter {0}'.format(x),
               'school': lambda x: ' From {0}'.format(x),
               'institution': lambda x: ' From {0}'.format(x),
               'journal': lambda x: x.name}

    @staticmethod
    def name_filter(persons: List[Person]) -> str:
        if len(persons) == 0:
            return ''
        persons = [str.title('{0.first_name} {0.last_name}'.format(author)) for author in persons]
        return '{0} & {1}'.format(', '.join(persons[0:-1]), persons[-1]) if len(persons) > 1 else persons[0]

    def __call__(self, entry: Item) -> str:
        str_list = [self.name_filter([x.person for x in entry.authorship]),
                    self.name_filter([x.person for x in entry.editorship])]
        for field_id in set(_field_ids):
            if hasattr(entry, field_id) and getattr(entry, field_id) is not None:
                value = getattr(entry, field_id)
                if field_id == 'number':
                    str_list.append('({0})'.format(value) if hasattr(entry, 'volume') else ' ' + str(value))
                else:
                    str_list.append(self.filters[field_id](value) if field_id in self.filters else value)
        return ', '.join([str(x) for x in str_list if x])


class BibtexFormatter(Formatter):
    _title_regex = re.compile(r'^(.+[A-Z].*)$')

    @staticmethod
    def title_filter(title: str) -> str:
        """escapes capitals because most bibtex systems apply title case"""
        return ' '.join((BibtexFormatter._title_regex.sub(r'{{\1}}', word.strip()) for word in title.split()))

    @staticmethod
    def name_filter(persons: List[Person]) -> str:
        return ' and '.join((str.title('{0.last_name}, {0.first_name}'.format(person)) for person in persons))

    _filters = {
        'author': name_filter,
        'editor': name_filter,
        'pdf_file': ', '.join,
        'comment_file': ', '.join,
        'keyword': ', '.join,
        'title': title_filter}

    def __init__(self, writer: BibTexWriter=None):
        self._bib_writer = writer

    def __call__(self, entry: Item) -> str:
        db = BibDatabase()
        entry_dict = dict()
        for field_id in set(_field_ids) & set(entry.__dict__):
            value = getattr(entry, field_id)
            if field_id in self._filters:
                entry_dict[field_id] = self._filters[field_id](value)
            else:
                entry_dict[field_id] = value
        writer = self._bib_writer if self._bib_writer else BibTexWriter()
        return writer.write(db)


class IdFormatter(Formatter):
    @staticmethod
    def name_filter(persons: List[Person]) -> str:
        return ''.join(map(lambda x: normalize('NFKD', x)[0], persons[0].last_name.lower().replace(' ', '')))

    def __call__(self, entry: Item, suffix: str=None):
        if len(entry.authorship) > 0:
            result_str = self.name_filter([x.person for x in entry.authorship])
        elif len(entry.editorship) > 0:
            result_str = self.name_filter([x.person for x in entry.editorship])
        else:
            result_str = 'anon'
        if hasattr(entry, 'year'):
            result_str += str(entry.year)
        else:
            result_str += entry.title.split()[0].title()
        if suffix:
            result_str += suffix
        return result_str
