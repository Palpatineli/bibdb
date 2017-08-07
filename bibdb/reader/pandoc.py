import json
import subprocess as sp
from os.path import isfile, splitext

from .main import Reader


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
        tokens = pandoc_dict[1]
        citation_list = list()
        for section in tokens:
            for token in section['c']:
                if type(token) is dict and token['t'] == 'Cite':
                    for citation in token['c'][0]:
                        citation_list.append(citation['citationId'])
        return citation_list
