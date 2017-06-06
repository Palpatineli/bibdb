from ..entry.main import Session, Item, Person, and_, Keyword
from ..entry.file_object import PdfFile, CommentFile
from ..formatter.aggregate import AuthoredList
from ..formatter.entry import SimpleFormatter, BibtexFormatter
from ..reader.pandoc import PandocReader


def search_paper(args):
    session = Session()
    if args.author:
        persons = session.query(Person).filter(Person.last_name == args.author).all()
        if len(persons) == 0:
            print("can't find author named " + args.author)
            return
        print(AuthoredList()(persons))
    elif args.keyword:
        keywords = {x.strip() for x in ' '.join(args.keyword).split(',')}
        item_list = session.query(Item).filter(and_(*(Item.keyword.any(Keyword.text == keyword)
                                                      for keyword in keywords))).all()
        if len(item_list) > 0:
            formatter = SimpleFormatter()
            print('\n'.join(formatter(item) for item in item_list))
        else:
            print('No item with keyword "{0}" has been found'.format('", "'.join(keywords)))


def delete_paper(args):
    session = Session()
    item = session.query(Item).filter(Item.id == args.paper_id).one()
    session.delete(item)
    session.commit()


def open_file(args):
    file_types = {'pdf'} if not (args.files and len(args.files) > 0) else set(args.files)
    session = Session()
    if not session.query(session.query(Item.id == args.paper_id).exists()):
        raise ValueError("can't find item with id " + args.paper_id)
    for file_type in file_types:
        if file_type == 'pdf':
            for file in session.query(PdfFile).filter(Item.id == args.paper_id).all():
                file.open()
        if file_type == 'comment':
            comment = session.query(CommentFile).filter(Item.id == args.paper_id).first()
            if comment is None:
                item = session.query(Item).filter(Item.id == args.paper_id).one()
                comment = CommentFile.new(item)
                item.file.append(comment)
                session.commit()
            comment.open()


def output(args):
    session = Session()
    if args.source.endswith('.ast') or args.source.endswith('.json'):
        item_list = session.query(Item).filter(Item.id.in_(PandocReader(args.source)())).all()
    elif args.source.lower() == 'all':
        item_list = session.query(Item).all()
    else:
        item_list = session.query(Item).filter(Item.id.in_(args.source.split(','))).all()
    if args.format == 'bib':
        print('\n'.join((BibtexFormatter()(item) for item in item_list)))
    elif args.format == 'str':
        print('\n'.join((SimpleFormatter()(item) for item in item_list)))


def modify_keyword(args):
    session = Session()
    item = session.query(Item).filter(Item.id == args.paper_id).one()
    if args.add:
        item.keyword.extend((Keyword(text=x.strip()) for x in ' '.join(args.add).split(',')))
    if args.delete:
        for x in ' '.join(args.delete).split(','):
            item.keyword.remove(Keyword(text=x.strip()))
    session.commit()
    print(SimpleFormatter()(item))
    print('\tKeywords: {0}'.format(', '.join((x.text for x in item.keyword))))


def initialize(_):
    from os import makedirs, path
    from shutil import copy2
    from zipfile import ZipFile
    from pkg_resources import Requirement, resource_filename, resource_stream
    from ..config import config, get_config_path
    from ..data.journal import add_journals
    # copy configuration file is not exist
    target_file = get_config_path()
    if not path.isfile(target_file):
        source_file = resource_filename(Requirement('bibdb'), 'bibdb/data/bibdb.json')
        print('moving example config file to ' + target_file)
        copy2(source_file, target_file)
    # create folders if not exist
    for file_path in config['path'].values():
        makedirs(path.split(path.expanduser(file_path))[0], exist_ok=True)
    for file_type in config['files'].values():
        makedirs(path.expanduser(file_type['folder']), exist_ok=True)
    # create journal names database
    with resource_stream(Requirement.parse('bibdb'), "bibdb/data/journals.zip") as file_stream:
        with ZipFile(file_stream) as zf:
            with zf.open(zf.namelist()[0]) as fp:
                add_journals(fp)
    # create main database
    from ..entry import main, file_object
    session = main.Session()
    main.ItemBase.metadata.create_all(main.engine)
    session.commit()
