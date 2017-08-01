from unicodedata import normalize


def normalized(string: str):
    """normalize unicode to their closest ascii letters"""
    return normalize('NFKD', string).encode('ascii', 'ignore').decode('utf-8')
