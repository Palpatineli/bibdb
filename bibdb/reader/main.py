from typing import Union, TextIO, BinaryIO
from abc import ABC, abstractmethod


class Reader(ABC):
    # noinspection PyUnusedLocal
    @abstractmethod
    def __init__(self, fp: Union[TextIO, BinaryIO]):
        raise NotImplementedError

    @abstractmethod
    def __call__(self):
        raise NotImplementedError
