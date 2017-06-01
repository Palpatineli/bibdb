from bibdb.entry import Session, Item, Person, and_, Keyword
from bibdb.entry.file_object import PdfFile, CommentFile
from bibdb.formatter.aggregate import AuthoredList
from bibdb.formatter import SimpleFormatter, BibtexFormatter
from bibdb.reader.pandoc import PandocReader


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
        item_list = session.query(Item).filter(and_(*(Item.keyword.has(keyword) for keyword in keywords)))
        formatter = SimpleFormatter()
        print('\n'.join(formatter(item) for item in item_list))


def delete_paper(args):
    session = Session()
    item = session.query(Item.id == args.paper_id).one()
    for file in item.file:
        file.delete()
    session.delete(item)


def open_file(args):
    file_types = {'pdf'} if not (args.files and len(args.files) > 0) else set(args.files)
    session = Session()
    if not session.query(session.query(Item.id == args.paper_id).exists()):
        raise ValueError("can't find item with id " + args.paper_id)
    for file_type in file_types:
        if file_type == 'pdf':
            for file in session.query(PdfFile).filter(PdfFile.item.id == args.paper_id).all():
                file.open()
        if file_type == 'comment':
            comment = session.query(CommentFile).filter(CommentFile.item.id == args.paper_id).first()
            if comment is None:
                item = session.query(Item).filter(Item.id == args.paper_id).one()
                comment = CommentFile.new(item)
                item.file.append(item)
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


def initialize(args):
    pass
