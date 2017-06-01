"""handles journal names and abbreviations in a separate database. only works with sqlite"""
from typing import Dict
from os.path import isfile
import sqlite3 as sql
from ..config import config

CREATE = 'CREATE VIRTUAL TABLE "journal" USING fts4("name", "abbr", "abbr_no_dot");'
SEARCH = 'SELECT * FROM journal WHERE journal MATCH ? ORDER BY LENGTH(name)'


def add_journals(file_name: str) -> None:
    journal_str = ('("{0}"), '.format('","'.join(line.split('\t'))) for line in open(file_name, 'r'))
    database_path = config['path']['journal_db']
    if not isfile(database_path):
        conn = sql.connect(database_path)
        conn.cursor().execute(CREATE)
        conn.commit()
    conn = sql.connect(database_path)
    cur = conn.cursor()
    cur.execute('PRAGMA synchronous = OFF')
    cur.execute('BEGIN TRANSACTION')
    cur.executemany('INSERT INTO "journal" VALUES ', journal_str)
    conn.commit()
    cur.execute('PRAGMA synchronous = NORMAL')


def search_journal(query: str) -> Dict[str, str]:
    database_path = config['path']['journal_db']
    conn = sql.connect(database_path)
    journal = conn.cursor().execute(SEARCH, query).fetchone()
    if journal is None:
        raise ValueError('cannot find matching journal name ' + query)
    return dict(zip(('name', 'abbr', 'abbr_no_dot'), journal))
