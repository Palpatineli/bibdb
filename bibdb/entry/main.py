from sqlalchemy import Column, Integer, String, UniqueConstraint, ForeignKey, Table
from sqlalchemy import create_engine, and_
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.event import listens_for

from ..config import config

SMALL_TEXT = String(50)
LARGE_TEXT = String(150)

engine = create_engine('sqlite:///{}'.format(config['path']['database']))
ItemBase = declarative_base()
Session = sessionmaker(engine)

all_fields = {'booktitle': SMALL_TEXT, 'address': LARGE_TEXT, 'month': Integer, 'school': SMALL_TEXT,
              'institution': SMALL_TEXT, 'publisher': SMALL_TEXT, 'chapter': Integer, 'organization': SMALL_TEXT,
              'pages': SMALL_TEXT, 'volume': Integer, 'number': Integer, 'series': Integer, 'type': SMALL_TEXT,
              'note': LARGE_TEXT, 'edition': Integer, 'howpublished': SMALL_TEXT}

extra_fields = {'doi': SMALL_TEXT, 'eprint': LARGE_TEXT, 'url': LARGE_TEXT, 'object_type': SMALL_TEXT}

item_table = Table('item', ItemBase.metadata,
                   Column('id', SMALL_TEXT, primary_key=True),
                   Column('title', LARGE_TEXT, unique=True, nullable=False),
                   Column('year', Integer, nullable=False),
                   Column('journal_id', Integer, ForeignKey("journal.id")),
                   *(Column(*key_value) for key_value in {**all_fields, **extra_fields}.items()))

keyword_assoc = Table('association', ItemBase.metadata,
                      Column('item_id', Integer, ForeignKey('item.id')),
                      Column('keyword_id', Integer, ForeignKey('keyword.id')))


class Item(ItemBase):
    """base class for all bib entry main table items"""
    __mapper_args__ = {'polymorphic_on': 'object_type'}
    __tablename__ = 'item'
    author = association_proxy("authorship", "person"),
    required_fields = {'id', 'title', 'year'}
    optional_fields = {'address', 'month', 'note', 'doi', 'eprint', 'url'}

    def __init__(self, in_data: dict):
        for field_id in self.required_fields | self.optional_fields:
            if field_id in in_data:
                setattr(self, field_id, in_data[field_id])


class Person(ItemBase):
    id = Column(Integer, primary_key=True)
    last_name = Column(SMALL_TEXT, index=True, nullable=False)
    first_name = Column(SMALL_TEXT, nullable=False)
    authored = association_proxy("authorship", "item")
    edited = association_proxy("editorship", "item")
    __tablename__ = "person"
    __table_args__ = (UniqueConstraint("last_name", "first_name"),)


class Authorship(ItemBase):
    item_id = Column(SMALL_TEXT, ForeignKey("item.id"), primary_key=True)
    item = relationship(Item, backref=backref("authorship", cascade="all, delete-orphan"))
    person_id = Column(Integer, ForeignKey("person.id"), primary_key=True)
    person = relationship(Person, backref="authorship")
    order = Column(Integer)
    note = Column(String)
    __tablename__ = "authorship"
    __table_args__ = (UniqueConstraint("item_id", "order"),)


class Editorship(ItemBase):
    item_id = Column(SMALL_TEXT, ForeignKey("item.id"), primary_key=True)
    item = relationship(Item, backref=backref("editorship", cascade="all, delete-orphan"))
    person_id = Column(Integer, ForeignKey("person.id"), primary_key=True)
    person = relationship(Person, backref="editorship")
    order = Column(Integer)
    note = Column(String)
    __tablename__ = "editorship"
    __table_args__ = (UniqueConstraint("item_id", "order"),)


class Keyword(ItemBase):
    __tablename__ = 'keyword'
    id = Column(Integer, primary_key=True)
    text = Column(SMALL_TEXT, unique=True)
    item = relationship(Item, secondary=keyword_assoc, backref="keyword")


@listens_for(Session, 'after_flush')
def delete_orphan_keyword(session, _):
    session.query(Keyword).filter(~Keyword.item.any()).delete(synchronize_session=False)


@listens_for(Session, 'after_flush')
def delete_orphan_person(session, _):
    session.query(Person).filter(and_(~Person.authored.any(), ~Person.edited.any())).delete(synchronize_session=False)


class Journal(ItemBase):
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    abbr = Column(String, unique=True)
    abbr_no_dot = Column(String, unique=True)
    __tablename__ = "journal"

    def __init__(self, data_in: dict):
        for key, value in data_in.items():
            if hasattr(self, key):
                setattr(self, key, value)


@listens_for(Session, 'after_flush')
def delete_orphan_journal(session, _):
    session.query(Journal).filter(and_(~Journal.article.any())).delete(synchronize_session=False)


## bibtex entry types
class Article(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'article'}
    journal = relationship(Journal, backref="article")
    required_fields = Item.required_fields | {'journal_id'}
    optional_fields = Item.optional_fields | {'pages', 'volume', 'number'}


class Book(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'book'}
    editor = association_proxy('editorship', 'person')
    required_fields = Item.required_fields | {'publisher'}
    optional_fields = Item.optional_fields | {'volume', 'number', 'series', 'edition'}


class Booklet(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'booklet'}
    required_fields = Item.required_fields - {'year'}
    optional_fields = Item.optional_fields | {'year', 'howpublished'}


class InBook(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'inbook'}
    editor = association_proxy('editorship', 'person')
    required_fields = Item.required_fields | {'publisher', 'chapter', 'pages'}
    optional_fields = Item.optional_fields | {'volume', 'number', 'series', 'type', 'edition'}


class InCollection(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'incollection'}
    editor = association_proxy('editorship', 'person')
    required_fields = Item.required_fields | {'booktitle', 'publisher'}
    optional_fields = Item.optional_fields | {'chapter', 'pages', 'volume', 'number', 'series', 'type', 'edition'}


class InProceedings(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'inproceedings'}
    editor = association_proxy('editorship', 'person')
    required_fields = Item.required_fields | {'booktitle'}
    optional_fields = Item.optional_fields | {'publisher', 'organization', 'pages', 'volume', 'number', 'series'}


class Manual(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'manual'}
    required_fields = (Item.required_fields - {'year'})
    optional_fields = Item.optional_fields | {'year', 'organization', 'edition'}


class MasterThesis(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'masterthesis'}
    required_fields = Item.required_fields | {'school'}
    optional_fields = Item.optional_fields | {'type'}


class Misc(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'misc'}
    required_fields = (Item.required_fields - {'year', 'title'})
    optional_fields = Item.optional_fields | {'title', 'howpublished'}


class PhdThesis(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'phdthesis'}
    required_fields = Item.required_fields | {'school'}
    optional_fields = Item.optional_fields | {'type'}


class Proceedings(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'proceedings'}
    editor = association_proxy('editorship', 'person')
    optional_fields = Item.optional_fields | {'publisher', 'organization', 'volume', 'number', 'series'}


class TechReport(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'techreport'}
    required_fields = Item.required_fields | {'institution'}
    optional_fields = Item.optional_fields | {'number', 'type'}


class Unpublished(Item):
    __mapper_args__ = {'polymorphic_on': 'object_type', 'polymorphic_identity': 'unpublished'}
    required_fields = (Item.required_fields - {'year'})
    optional_fields = Item.optional_fields | {'year'}


item_types = {'article': Article, 'book': Book,
              'inproceedings': InProceedings, 'unpublished': Unpublished,
              'incollection': InCollection, 'inbook': InBook, 'phdthesis': PhdThesis}
