import re
import html
import core.leaf_tokenizer as tokenizer

__all__ = ['EscapeSequence', 'Strong', 'Emphasis', 'InlineCode',
           'Strikethrough', 'Link']

class LeafToken(object):
    def __init__(self, content):
        token_types = [globals()[key] for key in __all__]
        fallback_token = RawText
        lt = tokenizer.LeafTokenizer(content, token_types, fallback_token)
        self.children = lt.get_tokens()

class Strong(LeafToken):
    pattern = re.compile(r"\*\*(.+)\*\*|__(.+)__")
    def __init__(self, raw):
        super().__init__(raw)

class Emphasis(LeafToken):
    pattern = re.compile(r"\*(.+)\*|_(.+)_")
    def __init__(self, raw):
        super().__init__(raw)

class InlineCode(LeafToken):
    pattern = re.compile(r"`(.+)`")
    def __init__(self, raw):
        super().__init__(raw)

class Strikethrough(LeafToken):
    pattern = re.compile(r"~~(.+)~~")
    def __init__(self, raw):
        super().__init__(raw)

class Link(LeafToken):
    pattern = re.compile(r"(\[(.+)\]\((.+)\))")
    def __init__(self, raw):
        self.name = raw[1:raw.index(']')]
        self.target = raw[raw.index('(')+1:-1]

class EscapeSequence(LeafToken):
    pattern = re.compile(r"\\([\*\(\)\[\]\~])")
    def __init__(self, raw):
        self.content = raw

class RawText(LeafToken):
    def __init__(self, content):
        self.content = content
