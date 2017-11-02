from argparse import ArgumentParser

from .actions import main as actions
from .actions.store_paper import store_paper


def parse_args():
    parser = ArgumentParser("bibdb", description="a tool to manage literature library",
                            epilog="citation is usually $first_author_last_name$year")
    subparsers = parser.add_subparsers(help='commands')

    search_parser = subparsers.add_parser('s', help='search paper')
    search_parser.set_defaults(func=actions.search_paper)
    search_parser.add_argument('-a', '--author')
    search_parser.add_argument('-k', '--keyword', nargs="+")

    open_parser = subparsers.add_parser('o', help='open file')
    open_parser.set_defaults(func=actions.open_file)
    open_parser.add_argument('paper_id')
    open_parser.add_argument('-c', '--comment', dest='files', action='append_const',
                             const='comment')
    open_parser.add_argument('-p', '--pdf', dest='files', action='append_const', const='pdf')

    add_parser = subparsers.add_parser('a', help='add entry')
    add_parser.set_defaults(func=store_paper)
    add_parser.add_argument('keyword', nargs="*", help='give a list of keyword separated by colons')

    add_parser = subparsers.add_parser('d', help='delete entry')
    add_parser.set_defaults(func=actions.delete_paper)
    add_parser.add_argument('paper_id')

    output_parser = subparsers.add_parser('u', help='output information')
    output_parser.set_defaults(func=actions.output)
    output_parser.add_argument('source', help='supply a list of paper ids or find Pandoc token '
                                              'file to extract a minimal reference list')
    output_format = output_parser.add_mutually_exclusive_group(required=True)
    output_format.add_argument('-b', '--bibtex', dest="format", action='store_const', const='bib',
                               help='output bibtex file')
    output_format.add_argument('-s', '--string', dest="format", action='store_const', const='str',
                               help='output a simple string')

    key_parser = subparsers.add_parser('k', help='manipulate keywords')
    key_parser.set_defaults(func=actions.modify_keyword)
    key_parser.add_argument('paper_id')
    key_parser.add_argument('-a', '--add', nargs="+", help='keywords to add, separate by colon')
    key_parser.add_argument('-d', '--delete', nargs="+", help='keywords to delete, separate by '
                                                              'colon')

    add_parser = subparsers.add_parser('init', help='initialize')
    add_parser.set_defaults(func=actions.initialize)

    args = parser.parse_args()
    args.func(args)
