from ..entry.main import Session, item_types, Item, Person, Authorship, Editorship, Keyword, Journal, and_
from ..entry.file_object import Unregistered, PdfFile
from ..formatter.entry import SimpleFormatter, FileNameFormatter
from ..reader.bibtex import BibtexReader
from ..data.journal import search_journal


class StorePaperException(Exception):
    pass


def store_paper(args):
    bib_file = Unregistered.find()
    entry = BibtexReader(bib_file.open())().entries[0]
    item = item_types[entry['ENTRYTYPE']](entry)
    new_keywords = {x.strip() for x in ' '.join(args.keyword).split(',')} if args.keyword else set()
    if 'keyword' in entry:
        new_keywords |= set(entry['keyword'])
    session = Session()

    try:
        print(item.title)
        try:
            temp_pdf_file = PdfFile.find('temp-pdf')
            print('\tFile: {0}'.format(temp_pdf_file.name))
        except IOError as e:
            print(e)
            temp_pdf_file = None
            print('\tFile: None')
        if input('(a)abort, (c)continue?') != 'c':
            print("aborted")
            return

        item.id = entry['author'][0][0] + str(entry['year'])
        while True:
            conflicting_item = session.query(Item).filter(Item.id == item.id).first()
            if conflicting_item is None:
                break
            print('citation conflict!\n' + SimpleFormatter()(conflicting_item))
            choice = input('(a)abort, (u)update entry, Input new citation?')
            if choice == 'a':
                raise StorePaperException("manually aborted")
            elif choice == 'u':
                item = conflicting_item
                new_keywords -= set(map(lambda x: x.text, conflicting_item.keyword))
                break
            else:
                item.id = choice

        update_keywords(session, new_keywords, item.keyword)

        if 'author' in entry:
            for idx, person in enumerate(entry['author']):
                add_person(session, person, idx, Authorship, item.authorship)
        if 'editor' in entry:
            for idx, person in enumerate(entry['editor']):
                add_person(session, person, idx, Editorship, item.editorship)

        if 'journal' in entry:
            set_journal(session, entry['journal'], item)

        if temp_pdf_file is not None:
            pdf_files = [file for file in item.file if isinstance(file, PdfFile)]
            if len(pdf_files) == 0:
                temp_pdf_file.move('pdf', FileNameFormatter()(item))
            else:  # add or replace file
                print("pdf_file exists!\n" + '\n'.join('{0}: {1.name}'.format(*x) for x in enumerate(pdf_files)))
                choice = input('(c)do nothing; (N) replace the Nth file; or put a short word as new '
                               'file\'s suffix: ')
                if choice != 'c':
                    try:
                        old_file = pdf_files[int(choice)]
                        new_name = old_file.name
                        item.file.remove(old_file)
                        session.delete(old_file)
                    except ValueError:
                        suffix = choice
                        new_name = FileNameFormatter()(entry, suffix)
                    temp_pdf_file.move('pdf', new_name)
            item.file.append(temp_pdf_file)
            session.add(temp_pdf_file)
        session.add(item)
        session.commit()
        print('successfully inserted the following entry:')
        print(SimpleFormatter()(session.query(Item).filter(Item.id == item.id).one()))
    except StorePaperException as e:
        session.rollback()
        print(e)
        return


def add_person(session, name, order, relation_class, proxy):
    last_name, first_name = map(str.lower, name)
    persons = session.query(Person).filter(Person.last_name == last_name).all()
    if len(persons) == 0:
        person = Person(last_name=last_name, first_name=first_name)
    else:
        match = [idx for idx, x in enumerate(persons) if first_name == x.first_name]
        if len(match) > 0:
            person = persons[match[0]]
        else:
            print(("Who's this author? ({0}, {1})".format(*name)))
            for idx, old_person in enumerate(persons):
                print(('{0}. {1}, {2}'.format(idx, old_person.last_name.title(),
                                              old_person.first_name.title())))
            choice = input("(a)abort, or type 'number,new_name'\n").lower().strip()
            new_name = None
            if ',' in choice:
                choice, new_name = [a.strip() for a in choice.split(',', maxsplit=2)]
            if choice == 'a':
                raise StorePaperException('manually aborted')
            elif choice == 'n':  # use new author
                person = Person(first_name=(new_name if new_name else first_name), last_name=last_name)
            else:
                person = persons[int(choice)]
                if new_name:
                    person.first_name = new_name
    exist_relation = session.query(relation_class).filter(and_(
        relation_class.order == order, Person.last_name == person.last_name,
        Person.first_name == person.first_name)).first()
    relation = exist_relation if exist_relation else relation_class(order=order, person=person)
    if relation not in proxy:
        proxy.append(relation)


def update_keywords(session, new_keywords, proxy):
    existing = session.query(Keyword).filter(Keyword.text.in_(new_keywords)).all()
    for keyword in existing:
        new_keywords -= {keyword.text}
        proxy.append(keyword)
    for keyword in new_keywords:
        proxy.append(Keyword(text=keyword))


def set_journal(session, journal_name, item):
    try:
        journal = search_journal(journal_name)
    except ValueError:
        raise StorePaperException
    existing = session.query(Journal).filter(Journal.name == journal['name']).first()
    journal = existing if existing else Journal(journal)
    item.journal = journal
