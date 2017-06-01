import os
from os import path, makedirs
from glob import glob
from abc import ABC
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

from ..config import get_config
from ..formatter import TitleFormatter

Base = declarative_base()
SMALL_TEXT = String(50)
LARGE_TEXT = String(150)

config = get_config()


class PdfError(ValueError):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Error: paper [{0}] doesn't have a pdf file".format(self.value)

    __str__ = __repr__


class NewSearchable(ABC):
    _object_type = ''

    @classmethod
    def find(cls, folder: str=None):
        folder = folder if folder else path.expanduser(config['files'][cls._object_type]['folder'])
        extension = config['files'][cls._object_type]['extension']
        if isinstance(extension, list):
            for ext in extension:
                file_list = glob(path.join(folder, '*' + ext))
                if len(file_list) == 0:
                    continue
                file_name = path.splitext(path.split(max(file_list, key=path.getatime))[1])[0]
                return cls(file_name, folder)
        raise FileNotFoundError("No {0} file in {1}".format(cls._object_type, folder))


class ItemFile(Base, NewSearchable):
    id = Column(Integer, primary_key=True)
    item_id = Column(SMALL_TEXT, ForeignKey("item.ID"), index=True)
    name = Column(LARGE_TEXT, nullable=False)
    note = Column(SMALL_TEXT)
    object_type = Column(SMALL_TEXT)
    item = relationship("item", backref=backref("file"))
    __tablename__ = 'file'
    __mapper_args__ = {'polymorphic_on': 'object_type'}

    def __init__(self, name: str, folder: str=None, note: str=None):
        self.folder = folder if folder else path.expanduser(config['files'][self._object_type]['folder'])
        self.name = name
        if note:
            self.note = note
        self.opener = config['files'][self._object_type]['opener']
        self.extension = config['files'][self._object_type]['extension']

    def __repr__(self) -> str:
        return path.join(self.folder, self.name + self.extension)

    def open(self):
        file_path = path.join(self.folder, self.file_name + self.extension)
        import subprocess
        if os.name == 'nt':
            detach_process = 0x00000008
            pid = subprocess.Popen([self.opener, file_path],
                                   creationflags=detach_process).pid
        else:
            devnull = open(os.devnull, 'wb')
            pid = subprocess.Popen(['nohup', self.opener, file_path],
                                   stdout=devnull, stderr=devnull).pid
        print(('a {0} file is opened (pid: {1})'.format(self._object_type, pid)))

    def move(self, new_folder: str=None, new_name: str=None) -> None:
        """update name to new_name or move to new folder"""
        old_path = repr(self)
        if new_folder:
            if new_folder in config['files']:
                new_folder = path.expanduser(config['files'][new_folder]['folder'])
            if not path.isdir(new_folder):
                makedirs(new_folder)
            self.folder = new_folder
        if new_name:
            self.name = new_name
        os.rename(old_path, repr(self))

    def delete(self):
        os.remove(repr(self))


class PdfFile(ItemFile):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'pdf'}
    _object_type = 'pdf'


class CommentFile(ItemFile):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'comment'}
    _object_type = 'comment'

    @classmethod
    def new(cls, entry):
        folder = path.expanduser(config['files']['comment']['folder'])
        if not path.isdir(folder):
            makedirs(folder)
        file_path = path.join(folder, entry.id + cls.extension)
        with open(file_path, 'w') as fp:
            fp.write(TitleFormatter()(entry))


class Unregistered(NewSearchable):
    _object_type = 'bib'

    def __init__(self, file_name: str, folder: str):
        self.extension = config['files'][self._object_type]['extension']
        self.file_path = path.join(folder, file_name + self.extension)

    def open(self):
        return open(self.file_path, 'r')
