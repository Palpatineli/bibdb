from io import StringIO
from sqlalchemy.orm import with_polymorphic
from sqlalchemy import not_, and_
from colorama import init
from .store_paper import update_keywords
from ..entry.file_object import PdfFile, CommentFile
from ..entry.main import Session, Item, Person, Keyword, Authorship
from ..formatter.entry import SimpleFormatter, BibtexFormatter, ColorFormatter, format_once
from ..reader.pandoc import PandocReader

init()

def search_paper(args):
    session = Session()
    if args.author:
        entry = with_polymorphic(Item, '*')
        entries = session.query(entry, Authorship.order).join(Authorship).join(Person)\
            .filter(Person.last_name==args.author).order_by(Person.first_name, entry.year).all()
        if len(entries) > 0:
            output = StringIO()
            formatter = ColorFormatter(output)
            for x, order in entries:
                formatter(x, order)
            print(output.getvalue())
        else:
            print("can't find author named " + args.author)
    elif args.keyword:
        entry = with_polymorphic(Item, '*')
        keywords = {x.strip() for x in ' '.join(args.keyword).split(',')}
        item_list = session.query(entry).filter(
            and_(*(Item.keyword.any(Keyword.text == keyword)
                   for keyword in keywords))).all()
        if len(item_list) > 0:
            output = StringIO()
            formatter = ColorFormatter(output)
            for item in item_list:
                formatter(item)
            print(output.getvalue())
        else:
            print('No item with keyword "{0}" has been found'.format('", "'.join(keywords)))


def delete_paper(args):
    session = Session()
    item = session.query(Item).filter(Item.id == args.paper_id).one()
    session.delete(item)
    session.commit()
    session.query(Person).filter(and_(not_(Person.editorship.any()), not_(Person.authorship.any()))).\
        delete(synchronize_session='fetch')
    print('entry with id {} has been deleted'.format(args.paper_id))


def open_file(args):
    file_types = {'pdf'} if not (args.files and len(args.files) > 0) else set(
        args.files)
    session = Session()
    item = session.query(Item).filter(Item.id == args.paper_id).all()
    if not item:
        raise ValueError("can't find item with id " + args.paper_id)
    item = item[0]
    if 'pdf' in file_types:
        has_file = False
        for file in item.file:
            if isinstance(file, PdfFile):
                file.open()
                has_file = True
        if not has_file:
            print('There is no pdf file for {}'.format(item.id))
    if 'comment' in file_types:
        for file in item.file:
            if isinstance(file, CommentFile):
                file.open()
                return
        comment = CommentFile.new(item)
        item.file.append(comment)
        session.commit()
        comment.open()


def output(args):
    from os.path import splitext
    session = Session()
    print("source: ", args.source)
    if splitext(args.source)[-1] in {'.ast', '.json', '.txt', '.md'}:
        item_list = session.query(Item).filter(
            Item.id.in_(PandocReader(args.source)())).all()
    elif args.source.lower() == 'all':
        item_list = session.query(Item).all()
    else:
        item_list = session.query(Item).filter(
            Item.id.in_(args.source.split(','))).all()

    if len(item_list) == 0:
        print('entry has not been found for id: {}'.format(args.source))
    buf = StringIO()
    if args.format == 'bib':
        formatter = BibtexFormatter(buf)
    elif args.format == 'str':
        formatter = SimpleFormatter(buf)
    else:
        return
    for item in item_list:
        formatter(item)
    print(buf.getvalue())


def modify_keyword(args):
    session = Session()
    item = session.query(Item).filter(Item.id == args.paper_id).one()
    if args.add:
        to_add = ' '.join(args.add).split(',')
        update_keywords(session, set(to_add), item.keyword)
    if args.delete:
        for x in ' '.join(args.delete).split(','):
            keyword = session.query(Keyword).filter(
                Keyword.text == x.strip()).one()
            item.keyword.remove(keyword)
    session.commit()
    print(format_once(SimpleFormatter, item))
    print('\tKeywords: {0}'.format(', '.join((x.text for x in item.keyword))))


def initialize(_):
    from os import makedirs, path
    from shutil import copy2
    from zipfile import ZipFile
    from pkg_resources import Requirement, resource_filename, resource_stream
    from bibdb.config import config, get_config_path
    from bibdb.data.journal import add_journals
    # copy configuration file is not exist
    target_file = get_config_path()
    if not path.isfile(target_file):
        source_file = resource_filename(
            Requirement.parse('bibdb'), 'bibdb/data/bibdb.json')
        print('moving example config file to ' + target_file)
        copy2(source_file, target_file)
    # create folders if not exist
    for file_path in config['path'].values():
        makedirs(path.split(path.expanduser(file_path))[0], exist_ok=True)
    for file_type in config['files'].values():
        makedirs(path.expanduser(file_type['folder']), exist_ok=True)
    # create journal names database
    with resource_stream(
            Requirement.parse('bibdb'),
            "bibdb/data/journals.zip") as file_stream:
        with ZipFile(file_stream) as zf:
            with zf.open(zf.namelist()[0]) as fp:
                add_journals(fp)
    # create main database
    from bibdb.entry import main
    session = main.Session()
    main.ItemBase.metadata.create_all(main.engine)
    session.commit()
