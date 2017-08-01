from unicodedata import normalize as _normalize


def normalize(string: str):
    """normalize unicode to their closest ascii letters"""
    return _normalize('NFKD', string).encode('ascii', 'ignore').decode('utf-8')
