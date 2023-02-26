"""
Built-in span-level token classes.
"""

import html
import re
from typing import Iterable
import mistletoe.span_tokenizer as tokenizer
from mistletoe import core_tokens, token


"""
Tokens to be included in the parsing process, in the order specified.
"""
__all__ = ['EscapeSequence', 'Strikethrough', 'AutoLink', 'CoreTokens',
           'InlineCode', 'LineBreak', 'RawText']


def tokenize_inner(content):
    """
    A wrapper around span_tokenizer.tokenize. Pass in all span-level token
    constructors as arguments to span_tokenizer.tokenize.

    Doing so (instead of importing span_token module in span_tokenizer)
    avoids cyclic dependency issues, and allows for future injections of
    custom token classes.

    _token_types variable is at the bottom of this module.

    See also: span_tokenizer.tokenize, block_token.tokenize.
    """
    return tokenizer.tokenize(content, _token_types)


def add_token(token_cls, position=1):
    """
    Allows external manipulation of the parsing process.
    This function is called in BaseRenderer.__enter__.

    Arguments:
        token_cls (SpanToken): token to be included in the parsing process.
    """
    _token_types.insert(position, token_cls)


def remove_token(token_cls):
    """
    Allows external manipulation of the parsing process.
    This function is called in BaseRenderer.__exit__.

    Arguments:
        token_cls (SpanToken): token to be removed from the parsing process.
    """
    _token_types.remove(token_cls)


def reset_tokens():
    """
    Resets global _token_types to all token classes in __all__.
    """
    global _token_types
    _token_types = [globals()[cls_name] for cls_name in __all__]


class Particle:
    def __init__(self, text: str, token: 'SpanToken', tag: str = None):
        self.text = text
        self.token = token
        self.tag = tag


class SpanToken(token.Token):
    parse_inner = True
    parse_group = 1
    precedence = 5

    def __init__(self, match):
        if not self.parse_inner:
            self.content = match.group(self.parse_group)

    def __contains__(self, text):
        if hasattr(self, 'children'):
            return any(text in child for child in self.children)
        return text in self.content

    @classmethod
    def find(cls, string):
        return cls.pattern.finditer(string)

    def flatten(self) -> Iterable[Particle]:
        """
        Return a flattened representation of the tree of span tokens rooted at this token.
        Overridden in subclasses.
        """
        yield from ()

    @classmethod
    def embed_span(cls, leader: Particle, tokens: Iterable['SpanToken'], trailer: Particle = None) -> Iterable[Particle]:
        """
        Flatten `tokens` and embed within a leader and a trailer.
        The trailer defaults to the same as the leader.
        """
        yield leader
        for token in tokens:
            yield from token.flatten()
        yield trailer or leader


class CoreTokens(SpanToken):
    """
    Represents core tokens (Strong, Emphasis, Image, Link) during the early stage of parsing.
    Replaced with objects of the proper classes in the final stage of parsing.
    """
    precedence = 3
    def __new__(self, match):
        return globals()[match.type](match)

    @classmethod
    def find(cls, string):
        return core_tokens.find_core_tokens(string, token._root_node)


class Strong(SpanToken):
    """
    Strong token. ("**some text**")
    This is an inline token. Its children are inline (span) tokens.
    One of the core tokens.

    Attributes:
        delimiter (str): delimiter character, either an asterisk or an underscore.
    """
    def __init__(self, match):
        self.delimiter = match.delimiter

    def flatten(self) -> Iterable[Particle]:
        return self.embed_span(Particle(self.delimiter * 2, self), self.children)


class Emphasis(SpanToken):
    """
    Emphasis token. ("*some text*")
    This is an inline token. Its children are inline (span) tokens.
    One of the core tokens.

    Attributes:
        delimiter (str): delimiter character, either an asterisk or an underscore.
    """
    def __init__(self, match):
        self.delimiter = match.delimiter

    def flatten(self) -> Iterable[Particle]:
        return self.embed_span(Particle(self.delimiter, self), self.children)


class InlineCode(SpanToken):
    """
    Inline code token. ("`some code`")
    This is an inline token with a single child of type RawText.

    Attributes:
        raw_content (str): the content with all formatting preserved.
    """
    pattern = re.compile(r"(?<!\\|`)(?:\\\\)*(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
    parse_inner = False
    parse_group = 2

    def __init__(self, match):
        content = match.group(self.parse_group)
        self.raw_content = content
        self.delimiter = match.group(1)
        content = content.replace('\n', ' ')
        if not content.isspace() and content.startswith(" ") and content.endswith(" "):
            content = content[1:-1]
        self.children = (RawText(content),)

    @classmethod
    def find(cls, string):
        matches = core_tokens._code_matches
        core_tokens._code_matches = []
        return matches

    def flatten(self) -> Iterable[Particle]:
        yield from (
            Particle(self.delimiter, self),
            Particle(self.raw_content, self),
            Particle(self.delimiter, self)
        )


class Strikethrough(SpanToken):
    """
    Strikethrough token. ("~~some text~~")
    This is an inline token. Its children are inline (span) tokens.
    """
    pattern = re.compile(r"(?<!\\)(?:\\\\)*~~(.+?)~~", re.DOTALL)

    def flatten(self) -> Iterable[Particle]:
        return self.embed_span(Particle('~~', self), self.children)


class Image(SpanToken):
    """
    Image token. ("![alt](src "title")")
    This is an inline token. Its children are inline (span) tokens holding the image description.
    One of the core tokens.

    Attributes:
        src (str): image source.
        title (str): image title (default to empty).
        dest_type (str): "uri" for a plain uri, "angle_uri" for an uri within angle brackets;
                         "full" or "collapsed" or "shortcut" for reference links.
        label (str): link label, for reference links.
        title_delimiter (str): the delimiter used for the title.
                               Single quote, double quote, or opening parenthesis.
    """
    repr_attributes = ("src", "title")
    def __init__(self, match):
        self.src = EscapeSequence.strip(match.group(2).strip())
        self.title = EscapeSequence.strip(match.group(3))
        self.dest_type = getattr(match, "dest_type", None)
        self.label = getattr(match, "label", None)
        self.title_delimiter = getattr(match, "title_delimiter", None)

    def flatten(self) -> Iterable[Particle]:
        return Link.flatten_inner(self, self.src, is_image=True)

class Link(SpanToken):
    """
    Link token. ("[name](target "title")")
    This is an inline token. Its children are inline (span) tokens holding the link text.
    One of the core tokens.

    Attributes:
        target (str): link target.
        title (str): link title (default to empty).
        dest_type (str): "uri" for a plain uri, "angle_uri" for an uri within angle brackets;
                         "full" or "collapsed" or "shortcut" for reference links.
        label (str): link label, for reference links.
        title_delimiter (str): the delimiter used for the title.
                               Single quote, double quote, or opening parenthesis.
    """
    repr_attributes = ("target", "title")
    def __init__(self, match):
        self.target = EscapeSequence.strip(match.group(2).strip())
        self.title = EscapeSequence.strip(match.group(3))
        self.dest_type = getattr(match, "dest_type", None)
        self.label = getattr(match, "label", None)
        self.title_delimiter = getattr(match, "title_delimiter", None)

    def flatten(self) -> Iterable[Particle]:
        return self.flatten_inner(self, self.target)

    @classmethod
    def flatten_inner(cls, token, target, is_image=False) -> Iterable[Particle]:
        yield from cls.embed_span(
            Particle("![" if is_image else "[", token),
            token.children,
            Particle("]", token)
        )
        
        if token.dest_type == "uri" or token.dest_type == "angle_uri":
            # "![" description "](" dest_part [" " title] ")"
            yield Particle("(", token)
            dest_part = "".join(("<", target, ">")) if token.dest_type == "angle_uri" else target
            yield Particle(dest_part, token, "dest_part")
            if token.title:
                yield from (
                    Particle(" ", token),
                    Particle(token.title_delimiter, token),
                    Particle(token.title, token, "title"),
                    Particle(')' if token.title_delimiter == '(' else token.title_delimiter, token)
                )
            yield Particle(")", token)
        elif token.dest_type == "full":
            # "![" description "][" label "]"
            yield from (
                Particle("[", token),
                Particle(token.label, token, "label"),
                Particle("]", token)
            )
        elif token.dest_type == "collapsed":
            # "![" description "][]"
            yield Particle("[]", token)
        else:
            # "![" description "]"
            pass


class AutoLink(SpanToken):
    """
    Autolink token. ("<http://www.google.com>")
    This is an inline token with a single child of type RawText.

    Attributes:
        children (list): a single RawText node for the link target.
        target (str): link target.
        mailto (bool): true iff the target looks like an email address, but does not have the "mailto:" prefix.
    """
    repr_attributes = ("target", "mailto")
    pattern = re.compile(r"(?<!\\)(?:\\\\)*<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^ <>]*?|[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)>")
    parse_inner = False

    def __init__(self, match):
        content = match.group(self.parse_group)
        self.children = (RawText(content),)
        self.target = content
        self.mailto = '@' in self.target and 'mailto' not in self.target.casefold()

    def flatten(self) -> Iterable[Particle]:
        yield Particle("<" + self.children[0].content + ">", self)


class EscapeSequence(SpanToken):
    """
    Escape sequence token. ("\*")
    This is an inline token with a single child of type RawText.

    Attributes:
        children (iterator): a single RawText node containing the escaped character.
    """
    pattern = re.compile(r"\\([!\"#$%&'()*+,-./:;<=>?@\[\\\]^_`{|}~])")
    parse_inner = False
    precedence = 2

    def __init__(self, match):
        self.children = (RawText(match.group(self.parse_group)),)

    def flatten(self) -> Iterable[Particle]:
        yield Particle("\\" + self.children[0].content, self)

    @classmethod
    def strip(cls, string):
        return html.unescape(cls.pattern.sub(r'\1', string))


class LineBreak(SpanToken):
    """
    Line break token: hard or soft.
    This is an inline token without children.

    Attributes:
        content (str): always empty.
        soft (bool): true if this is a soft line break.
        marker (str): the marker used to identify a hard line break, either (at least) double spaces or a backslash.
    """
    repr_attributes = ("soft",)
    pattern = re.compile(r'( *|\\)\n')
    parse_inner = False
    parse_group = 0

    def __init__(self, match):
        self.content = ""
        self.marker = match.group(1)
        self.soft = not self.marker.startswith(('  ', '\\'))

    def flatten(self) -> Iterable[Particle]:
        yield Particle(self.marker + "\n", self)


class RawText(SpanToken):
    """
    Raw text token.
    This is an inline token without children.

    RawText is the only token that accepts a string for its constructor,
    instead of a match object. Also, all recursions should bottom out here.
    """
    def __init__(self, content):
        self.content = content

    def flatten(self) -> Iterable[Particle]:
        yield Particle(self.content, self)


_tags = {'address', 'article', 'aside', 'base', 'basefont', 'blockquote',
        'body', 'caption', 'center', 'col', 'colgroup', 'dd', 'details',
        'dialog', 'dir', 'div', 'dl', 'dt', 'fieldset', 'figcaption', 'figure',
        'footer', 'form', 'frame', 'frameset', 'h1', 'h2', 'h3', 'h4', 'h5',
        'h6', 'head', 'header', 'hr', 'html', 'iframe', 'legend', 'li', 'link',
        'main', 'menu', 'menuitem', 'meta', 'nav', 'noframes', 'ol',
        'optgroup', 'option', 'p', 'param', 'section', 'source', 'summary',
        'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'title', 'tr', 'track',
        'ul'}

_tag   = r'[A-Za-z][A-Za-z0-9-]*'
_attrs = r'(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*?\'|"[^\"]*?"))?)*'

_open_tag    = r'(?<!\\)<' + _tag + _attrs + r'\s*/?>'
_closing_tag = r'(?<!\\)</' + _tag + r'\s*>'
_comment     = r'(?<!\\)<!--(?!>|->)(?:(?!--).)+?(?<!-)-->'
_instruction = r'(?<!\\)<\?.+?\?>'
_declaration = r'(?<!\\)<![A-Z].+?>'
_cdata       = r'(?<!\\)<!\[CDATA.+?\]\]>'


class HTMLSpan(SpanToken):
    """
    Span-level HTML token.
    This is an inline token without children.

    Attributes:
        content (str): the raw HTML content.
    """
    pattern = re.compile('|'.join([_open_tag, _closing_tag, _comment,
                                   _instruction, _declaration, _cdata]),
                                   re.DOTALL)
    parse_inner = False
    parse_group = 0

    def flatten(self) -> Iterable[Particle]:
        yield Particle(self.content, self)


# Note: The following XWiki tokens are based on the XWiki Syntax 2.0 (or above; 1.0 was deprecated years ago already).

class XWikiBlockMacroStart(SpanToken):
    """
    A "block" macro opening tag. ("{{macroName<optionalParams>}}<newLine>") 
    
    We want to keep it on a separate line instead of "soft" merging it with the *following* line.
    """
    pattern = re.compile(r'(?<!\\)(\{\{\w+.*?(?<![\\/])\}\})\s*\n')
    parse_inner = False
    parse_group = 1

class XWikiBlockMacroEnd(SpanToken):
    """
    A "block" macro closing tag. ("<onlySpacesAllowed>{{/macroName}}") 
    
    We want to keep it on a separate line instead of "soft" merging it with the *preceding* line.
    """
    pattern = re.compile(r'^(?:\s*)(\{\{/\w+\}\})', re.MULTILINE)
    parse_inner = False
    parse_group = 1

_token_types = []
reset_tokens()
