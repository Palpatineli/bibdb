from os import path, remove
from unittest import TestCase
from zipfile import ZipFile

from bibdb.data.journal import add_journals, search_journal, config
from pkg_resources import resource_stream, Requirement

JOURNAL_LIST_FILE = "bibdb/data/journals.zip"


class TestJournalUtil(TestCase):
    real_journal_db_path = ''
    fp = None
    zf = None
    file_stream = None

    def setUp(self):
        self.real_journal_db_path = config['path']['journal_db']
        config['path']['journal_db'] = path.expanduser('~/temp_journal.sqlite')
        self.file_stream = resource_stream(Requirement.parse('bibdb'), JOURNAL_LIST_FILE)
        self.zf = ZipFile(self.file_stream)
        self.fp = self.zf.open(self.zf.namelist()[0])

    def test_add_journals(self):
        add_journals(self.fp)
        remove(config['path']['journal_db'])

    def test_search_journal(self):
        add_journals(self.fp)
        result = search_journal('Acta Crystallogr. A')
        assert(result['name'] == 'Acta Crystallographica. Section A, Foundations of Crystallography')
        try:
            search_journal('shitshitshit')
        except ValueError:
            pass
        remove(config['path']['journal_db'])

    def tearDown(self):
        self.fp.close()
        self.zf.close()
        self.file_stream.close()
        config['path']['journal_db'] = self.real_journal_db_path
