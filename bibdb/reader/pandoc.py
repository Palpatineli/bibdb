from typing import List
import json
import subprocess as sp
from os.path import isfile, splitext

from .main import Reader

def recurse(x, buffer: List[str]):
    dtype = type(x)
    if dtype is dict:
        if x['t'] == 'Cite':
            recurse_cite(x['c'], buffer)
        elif 'c' in x:
            recurse(x['c'], buffer)
    elif dtype is list:
        for item in x:
            recurse(item, buffer)

def recurse_cite(x, buffer: List[str]):
    dtype = type(x)
    if dtype is dict:
        if "citationId" in x:
            buffer.append(x["citationId"])
            return
        elif 'c' in x:
            dtype_1 = type(x['c'])
            if dtype_1 is list or dtype_1 is dict:
                recurse_cite(x['c'], buffer)
    elif dtype is list:
        for item in x:
            recurse_cite(item, buffer)

class PandocReader(Reader):
    # noinspection PyMissingConstructor
    def __init__(self, file_path: str):
        if isfile(file_path):
            ext = splitext(file_path)[-1]
            if ext in {'.ast', '.json'}:
                self.input = open(file_path, 'r', encoding='UTF-8').read()
            elif ext in {'.txt', '.markdown', '.md'}:
                try:
                    output = sp.check_output(['pandoc', '-f', 'markdown', '-t', 'json', file_path])
                except FileNotFoundError as e:
                    print("please install pandoc for citation extraction")
                    raise e
                self.input = output.decode('utf-8')
            else:
                raise ValueError('expected inputs are either markdown files or their pandoc treated ast '
                                 'files (in json)')
        else:
            self.input = file_path

    def __call__(self) -> list:
        pandoc_dict = json.loads(self.input)
        tokens = pandoc_dict['blocks']
        citation_list: List[str] = list()
        recurse(tokens, citation_list)
        return citation_list
