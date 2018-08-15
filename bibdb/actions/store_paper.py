from ..data.journal import search_journal
from ..entry.file_object import Unregistered, PdfFile, CommentFile
from ..entry.main import Session, item_types, Item, Person, Authorship, Editorship, Keyword, Journal
from ..formatter.entry import SimpleFormatter, FileNameFormatter, format_once
from ..reader.bibtex import BibtexReader
from ..utils import normalize


class StorePaperException(Exception):
    pass


def fix_authorship():
    import sys
    session = Session()
    entries = BibtexReader(open(sys.argv[1], 'r'))().entries
    for entry in entries:
        item = session.query(Item).filter(Item.id == entry['ID']).first()
        if item:
            if 'author' in entry:
                try:
                    author_number = len(entry['author'])
                    authors = session.query(Authorship).join(Item).filter(Item.id == item.id).all()
                    for missing_number in set(range(author_number)) - set([author.order for author in authors]):
                        author = session.query(Person).join(Authorship). \
                            filter((Person.last_name == entry['author'][missing_number][0]) &
                                   (Authorship.order == missing_number)).first()
                        if author:
                            relationship = Authorship(item=item, order=missing_number, person=author)
                            session.add(relationship)
                            session.commit()
                except Exception as e:
                    print(entry['author'])
                    session.rollback()
                    # noinspection PyUnboundLocalVariable
                    print(item.id, set(range(author_number)), set([author.order for author in authors]),
                          set(range(author_number)) - set([author.order for author in authors]))
                    raise e
            if 'editor' in entry:
                editor_number = len(entry['editor'])
                editors = session.query(Editorship).join(Item).filter(Item.id == entry['ID']).all()
                for missing_number in set(range(editor_number)) - set([editor.order for editor in editors]):
                    editor = session.query(Person).join(Editorship). \
                        filter((Person.last_name == entry['editor'][missing_number][0]) &
                               (Editorship.order == missing_number)).first()
                    if editor:
                        relationship = Editorship(item=item, order=missing_number, person=editor)
                        session.add(relationship)
    session.commit()


def import_bib():
    def add_person_direct(name, order, relation_class, proxy):
        last_name, first_name = map(str.lower, name)
        persons = session.query(Person).filter((Person.last_name == last_name) &
                                               (Person.first_name == first_name)).all()
        if len(persons) == 0:
            person_obj = Person(last_name=last_name, first_name=first_name)
        else:
            person_obj = persons[0]
        relation = relation_class(order=order, person=person_obj)
        if relation not in proxy:
            proxy.append(relation)

    import sys
    session = Session()
    entries = BibtexReader(open(sys.argv[1], 'r'))().entries
    for entry in entries:
        item = session.query(Item).filter((Item.title == entry['title']) | (Item.id == entry['ID'])).first()
        if item:
            continue
        try:
            item = item_types[entry['ENTRYTYPE']](entry)
            if 'keyword' in entry:
                update_keywords(session, set(entry['keyword']), item.keyword)
            if 'author' in entry:
                for idx, person in enumerate(entry['author']):
                    add_person_direct(person, idx, Authorship, item.authorship)
            if 'editor' in entry:
                for idx, person in enumerate(entry['editor']):
                    add_person_direct(person, idx, Editorship, item.editorship)
            if 'journal' in entry:
                set_journal(session, entry['journal'], item)
            if 'pdf_file' in entry:
                for file_name in entry['pdf_file']:
                    pdf_file = PdfFile(file_name)
                    item.file.append(pdf_file)
                    session.add(pdf_file)
            if 'comment_file' in entry:
                for file_name in entry['comment_file']:
                    comment_file = CommentFile(file_name)
                    item.file.append(comment_file)
                    session.add(comment_file)
            session.add(item)
            session.commit()
        except StorePaperException as e:
            session.rollback()
            raise e


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

        entry['author'] = [(normalize(last_name), normalize(first_name)) for last_name, first_name in entry['author']]
        if not (('author' in entry) or ('editor' in entry)) or ('year' not in entry):
            item.id = entry['ID']
        else:
            temp_str = (entry['author'][0][0] if 'author' in entry else entry['editor'][0][0]) + str(entry['year'])
            item.id = temp_str.replace(' ', '-')

        while True:
            conflicting_item = session.query(Item).filter((Item.id == item.id) | (Item.title == item.title)).first()
            if conflicting_item is None:
                break
            print('citation conflict!\n' + format_once(SimpleFormatter, conflicting_item))
            choice = input('(a)abort, (u)update entry, Input new citation?')
            if choice == 'a':
                raise StorePaperException("manually aborted")
            elif choice == 'u':
                for field in item.required_fields | item.optional_fields:
                    if hasattr(item, field):
                        setattr(conflicting_item, field, getattr(item, field))
                item = conflicting_item
                conflicting_item.authorship[:] = []
                break
            else:
                item.id = choice

        update_keywords(session, new_keywords, item.keyword)

        for idx, person in enumerate(entry.get('author', [])):
            add_person(session, person, idx, Authorship, item.authorship, item.id)
        for idx, person in enumerate(entry.get('editor', [])):
            add_person(session, person, idx, Editorship, item.editorship, item.id)

        if 'journal' in entry:
            set_journal(session, entry['journal'], item)

        if temp_pdf_file is not None:
            pdf_files = [file for file in item.file if isinstance(file, PdfFile)]
            if len(pdf_files) == 0:
                temp_pdf_file.move('pdf', format_once(FileNameFormatter, item))
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
                        new_name = format_once(FileNameFormatter, item, suffix)
                    temp_pdf_file.move('pdf', new_name)
            item.file.append(temp_pdf_file)
            session.add(temp_pdf_file)
        session.add(item)
        session.commit()
        print('successfully inserted the following entry:')
        print(format_once(SimpleFormatter, item))
    except StorePaperException as e:
        session.rollback()
        print(e)
        return


def add_person(session, name, order, relation_class, proxy, item_id):
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
    exist_relation = session.query(relation_class).filter(
        (relation_class.order == order) & (relation_class.person == person) &
        (relation_class.item_id == item_id)).first()
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
    while True:
        journal = search_journal(journal_name)
        if journal is None:
            existing = session.query(Journal).filter(Journal.name == journal_name).first()
            if existing:
                item.journal = existing
                return
            else:
                print('journal name not found: ' + journal_name)
                # noinspection SpellCheckingInspection
                choice = input('please input journal name, abbreviation, and abbreviation without dot form. '
                               'or (a)bort: ')
                if choice == 'a' or choice == '':
                    raise StorePaperException
                names = list(map(str.strip, choice.split(',')))
                if len(names) == 1:
                    journal_name = names
                elif len(names) == 3:
                    existing = session.query(Journal).filter(Journal.name == names[0]).first()
                    if existing:
                        existing.abbr, existing.abbr_no_dot = names[1], names[2]
                        item.journal = existing
                    else:
                        item.journal = Journal(dict(zip(('name', 'abbr', 'abbr_no_dot'), names)))
                    return
        else:
            existing = session.query(Journal).filter(Journal.name == journal['name']).first()
            journal = existing if existing else Journal(journal)
            item.journal = journal
            return
