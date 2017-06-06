import os
from os import path, makedirs
from glob import glob
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref, reconstructor

from ..formatter.entry import TitleFormatter
from .main import ItemBase, config, listens_for, Session

SMALL_TEXT = String(50)
LARGE_TEXT = String(150)


class PdfError(ValueError):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "Error: paper [{0}] doesn't have a pdf file".format(self.value)

    __str__ = __repr__


class NewSearchable(object):
    _object_type = ''

    @classmethod
    def find(cls, folder: str=None):
        if folder and path.isdir(folder):
            folder = folder
        else:
            folder = path.expanduser(config['files'][folder if folder else cls._object_type]['folder'])
        extension = config['files'][cls._object_type]['extension']
        if not isinstance(extension, list):
            extension = [extension]
        for ext in extension:
            file_list = glob(path.join(folder, '*' + ext))
            if len(file_list) == 0:
                continue
            file_name = path.splitext(path.split(max(file_list, key=path.getatime))[1])[0]
            return cls(file_name, folder, ext)
        raise FileNotFoundError("No {0} file in {1}".format(cls._object_type, folder))


class ItemFile(ItemBase, NewSearchable):
    id = Column(Integer, primary_key=True)
    item_id = Column(SMALL_TEXT, ForeignKey("item.id"), index=True)
    name = Column(LARGE_TEXT, nullable=False)
    note = Column(SMALL_TEXT)
    object_type = Column(SMALL_TEXT)
    item = relationship('Item', backref=backref("file"))
    __tablename__ = 'file'
    __mapper_args__ = {'polymorphic_on': 'object_type'}

    def __init__(self, name: str, folder: str=None, extension: str=None, note: str=None):
        self.folder = folder if folder else path.expanduser(config['files'][self._object_type]['folder'])
        self.name = name
        if note:
            self.note = note
        self.opener = config['files'][self._object_type]['opener']
        self.extension = extension if extension else config['files'][self._object_type]['extension']

    @reconstructor
    def init_on_load(self):
        self.folder = path.expanduser(config['files'][self._object_type]['folder'])
        self.opener = config['files'][self._object_type]['opener']
        self.extension = config['files'][self._object_type]['extension']

    def __repr__(self) -> str:
        return path.join(self.folder, self.name + self.extension)

    def open(self):
        file_path = path.join(self.folder, self.name + self.extension)
        import subprocess
        if os.name == 'nt':
            detach_process = 0x00000008
            pid = subprocess.Popen([self.opener, file_path],
                                   creationflags=detach_process).pid
        else:
            print(self.opener, file_path)
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


@listens_for(Session, 'after_flush')
def delete_orphan_file(session, _):
    files = session.query(ItemFile).filter(~ItemFile.item.has()).all()
    for file in files:
        file.delete()
        session.delete(file)


class PdfFile(ItemFile):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'pdf'}
    _object_type = 'pdf'

    def __init__(self, *args, **kwargs):
        super(PdfFile, self).__init__(*args, **kwargs)


class CommentFile(ItemFile):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'comment'}
    _object_type = 'comment'

    @classmethod
    def new(cls, entry):
        obj = cls(entry.id)
        with open(repr(obj), 'w') as fp:
            fp.write(TitleFormatter()(entry))
        return obj


class Unregistered(NewSearchable):
    _object_type = 'bib'

    def __init__(self, file_name: str, folder: str, extension: str):
        self.extension = config['files'][self._object_type]['extension']
        self.file_path = path.join(folder, file_name + extension)

    def open(self):
        return open(self.file_path, 'r')
