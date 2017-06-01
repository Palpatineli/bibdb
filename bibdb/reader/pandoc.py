from typing import TextIO, Union
import json
from .main import Reader


class PandocReader(Reader):
    # noinspection PyMissingConstructor
    def __init__(self, fp: Union[TextIO, str]):
        if isinstance(fp, str):
            self.fp = open(fp, 'r', encoding='UTF-8')
        else:
            self.fp = fp

    def __call__(self) -> list:
        pandoc_dict = json.load(self.fp)
        tokens = pandoc_dict[1]
        citation_list = list()
        for section in tokens:
            for token in section['c']:
                if type(token) is dict and token['t'] == 'Cite':
                    for citation in token['c'][0]:
                        citation_list.append(citation['citationId'])
        return citation_list
