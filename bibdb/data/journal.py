"""handles journal names and abbreviations in a separate database. only works with sqlite"""
from typing import Dict, Union
from io import BufferedIOBase, TextIOWrapper
from os.path import isfile
import sqlite3 as sql
from ..config import config

CREATE = 'CREATE VIRTUAL TABLE "journal" USING fts4("name", "abbr", "abbr_no_dot");'
SEARCH = 'SELECT * FROM journal WHERE journal MATCH ? ORDER BY LENGTH(name)'


def add_journals(file_name: Union[str, BufferedIOBase]) -> None:
    fp = open(file_name, 'r') if isinstance(file_name, str) else TextIOWrapper(file_name, 'utf-8')
    new_journals = (line.split('\t') for line in fp)
    database_path = config['path']['journal_db']
    if not isfile(database_path):
        conn = sql.connect(database_path)
        conn.cursor().execute(CREATE)
        conn.commit()
    conn = sql.connect(database_path)
    cur = conn.cursor()
    cur.execute('PRAGMA synchronous = OFF')
    cur.execute('BEGIN TRANSACTION')
    cur.executemany('INSERT INTO "journal" VALUES (?, ?, ?)', new_journals)
    conn.commit()
    cur.execute('PRAGMA synchronous = NORMAL')


def search_journal(query: str) -> Dict[str, str]:
    database_path = config['path']['journal_db']
    conn = sql.connect(database_path)
    journal = conn.cursor().execute(SEARCH, (query, )).fetchone()
    if journal is None:
        raise ValueError('cannot find matching journal name ' + query)
    return dict(zip(('name', 'abbr', 'abbr_no_dot'), journal))
