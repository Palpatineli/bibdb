import json
import os
from io import TextIOWrapper
from os.path import isfile, expanduser, expandvars

from pkg_resources import Requirement, resource_stream


def get_config_path() -> str:
    if os.name == 'nt':
        return expandvars('%appdata/bibdb.json')
    elif os.name == 'posix' or os.name == 'mac':
        return expanduser('~/.config/bibdb.json')


def get_config():
    config_path = get_config_path()
    if isfile(config_path):
        config_dict = json.load(open(config_path, 'r'))
    else:
        config_dict = json.load(TextIOWrapper(resource_stream(Requirement.parse('bibdb'), "bibdb/data/bibdb.json"),
                                              'utf-8'))
    if 'path' in config_dict:
        config_dict['path'].update({key: expanduser(value) for key, value in config_dict['path'].items()})
    return config_dict


config = get_config()
