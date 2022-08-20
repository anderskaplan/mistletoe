"""
Markdown renderer for mistletoe.

This renderer is designed to make as "clean" a roundtrip as possible, markdown -> parsing -> rendering -> markdown,
except for nonessential whitespace.
"""

import re
from itertools import chain

from mistletoe import block_token, span_token
from mistletoe.base_renderer import BaseRenderer


class BlankLine(block_token.BlockToken):
    """
    Blank line token. Represents a single blank line.
    This is a leaf block token without children.
    """
    pattern = re.compile(r'\s*\n$')

    def __init__(self, _):
        pass

    @classmethod
    def start(cls, line):
        return cls.pattern.match(line)

    @classmethod
    def read(cls, lines):
        return [next(lines)]


class LinkReferenceDefinition(block_token.BlockToken):
    """
    Link reference definition. ([label]: dest "title")
    This is a leaf block token without children.

    Not included in the parsing process, but called by LinkReferenceDefinitionBlock.
    """
    def __init__(self, match):
        self.label, self.dest, self.title, self.dest_type, self.title_tag = match


class LinkReferenceDefinitionBlock(block_token.Footnote):
    """
    A sequence of "link reference definitions".
    This is a container block token. Its children are link reference definition tokens.

    This class inherits from Footnote and modifies the behavior of the constructor so
    that the tokens are retained in the AST.
    """
    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.__init__(*args, **kwargs)
        return obj

    def __init__(self, matches):
        self.children = list(map(LinkReferenceDefinition, matches))


class MarkdownRenderer(BaseRenderer):
    """
    Markdown renderer.
    """
    def __init__(self, *extras):
        block_token.remove_token(block_token.Footnote)
        super().__init__(*chain((block_token.HTMLBlock, span_token.HTMLSpan, BlankLine, LinkReferenceDefinitionBlock), extras))
        self.render_map["SetextHeading"] = self.render_setext_heading
        self.render_map["CodeFence"] = self.render_fenced_code_block
        self.render_map["LinkReferenceDefinition"] = self.render_link_reference_definition
        self.indentation = ""
        self.is_at_beginning_of_line = True

    def indent(self):
        if self.is_at_beginning_of_line:
            self.is_at_beginning_of_line = False
            return self.indentation
        else:
            return ""

    def indent_and_feed_line(self, line):
        content = "".join((self.indentation if self.is_at_beginning_of_line else "", line, "\n"))
        self.is_at_beginning_of_line = True
        return content

    def indent_lines(self, lines):
        return "".join(map(self.indent_and_feed_line, lines))

    # span/inline tokens

    def render_raw_text(self, token) -> str:
        return "".join((self.indent(), token.content))

    def render_strong(self, token: span_token.Strong) -> str:
        return "".join((self.indent(), token.tag * 2, self.render_inner(token), token.tag * 2))

    def render_emphasis(self, token: span_token.Emphasis) -> str:
        return "".join((self.indent(), token.tag, self.render_inner(token), token.tag))

    def render_inline_code(self, token: span_token.InlineCode) -> str:
        return "".join((self.indent(), '`', self.render_inner(token), '`'))

    def render_strikethrough(self, token: span_token.Strikethrough) -> str:
        return "".join((self.indent(), '~~', self.render_inner(token), '~~'))

    def render_image(self, token: span_token.Image) -> str:
        return self.render_image_or_link(token, '!', token.src)

    def render_link(self, token: span_token.Link) -> str:
        return self.render_image_or_link(token, '', token.target)

    def render_image_or_link(self, token, prefix, target):
        indent = self.indent() # note: must call self.indent() before self.render_inner(token)
        if token.dest_type == "uri" or token.dest_type == "angle_uri":
            if token.dest_type == "angle_uri":
                dest_part = "".join(("<", target, ">"))
            else:
                dest_part = target
            if len(token.title) > 0:
                closer = ')' if token.title_tag == '(' else token.title_tag
                title_part = " {}{}{}".format(token.title_tag, token.title, closer)
            else:
                title_part = ""
            return "{}{}[{}]({}{})".format(indent, prefix, self.render_inner(token), dest_part, title_part)
        else:
            if token.dest_type == "full":
                text_part = "[{}]".format(self.render_inner(token))
                dest_part = token.dest
            elif token.dest_type == "collapsed":
                text_part = "[{}]".format(self.render_inner(token))
                dest_part = ""
            else:
                text_part = ""
                dest_part = self.render_inner(token)
            return "{}{}{}[{}]".format(indent, prefix, text_part, dest_part)

    def render_auto_link(self, token: span_token.AutoLink) -> str:
        return "".join((self.indent(), "<", self.render_inner(token), ">"))

    def render_escape_sequence(self, token: span_token.EscapeSequence) -> str:
        return "".join((self.indent(), "\\", self.render_inner(token)))

    def render_line_break(self, token: span_token.LineBreak) -> str:
        content = "".join((self.indent(), token.tag, "\n"))
        self.is_at_beginning_of_line = True
        return content

    def render_html_span(self, token: span_token.HTMLSpan) -> str:
        return "".join((self.indent(), token.content))

    # block tokens

    def render_heading(self, token: block_token.Heading) -> str:
        trailer_part = "".join((" ", token.trailer)) if len(token.trailer) > 0 else ""
        content = "".join((self.indent(), "#" * token.level, " ", self.render_inner(token), trailer_part, "\n"))
        self.is_at_beginning_of_line = True
        return content

    def render_setext_heading(self, token: block_token.SetextHeading) -> str:
        char = "=" if token.level == 1 else "-"
        content = "".join((self.indent(), self.render_inner(token), "\n", char * token.tag_length, "\n"))
        self.is_at_beginning_of_line = True
        return content

    def render_quote(self, token: block_token.Quote) -> str:
        prefix = "".join((self.indent(), "> "))
        prev_indentation = self.indentation
        self.indentation += "> "
        self.is_at_beginning_of_line = False
        content = "".join((prefix, self.render_inner(token), "\n" if not self.is_at_beginning_of_line else ""))
        self.is_at_beginning_of_line = True
        self.indentation = prev_indentation
        return content

    def render_paragraph(self, token: block_token.Paragraph) -> str:
        content = "".join((self.indent(), self.render_inner(token), "\n"))
        self.is_at_beginning_of_line = True
        return content

    def render_block_code(self, token: block_token.BlockCode) -> str:
        prev_indentation = self.indentation
        self.indentation += "    "
        lines = token.children[0].content[:-1].split("\n")
        content = self.indent_lines(lines)
        self.indentation = prev_indentation
        return content

    def render_fenced_code_block(self, token: block_token.BlockCode) -> str:
        prev_indentation = self.indentation
        self.indentation += " " * token.indentation
        def make_lines():
            yield "".join((token.tag, token.info_string))
            for line in token.children[0].content[:-1].split("\n"):
                yield line
            yield token.tag
        content = self.indent_lines(make_lines())
        self.indentation = prev_indentation
        return content

    def render_list(self, token: block_token.List) -> str:
        return self.render_inner(token)

    def render_list_item(self, token: block_token.ListItem) -> str:
        prefix = "".join((self.indent(), token.leader, " "))
        prev_indentation = self.indentation
        self.indentation += " " * (len(token.leader) + 1)
        self.is_at_beginning_of_line = False
        content = "".join((prefix, self.render_inner(token), "\n" if not self.is_at_beginning_of_line else ""))
        self.is_at_beginning_of_line = True
        self.indentation = prev_indentation
        return content

    # def render_table(self, token: block_token.Table) -> str:
    #     return self.render_inner(token)

    # def render_table_cell(self, token: block_token.TableCell) -> str:
    #     return self.render_inner(token)

    # def render_table_row(self, token: block_token.TableRow) -> str:
    #     return self.render_inner(token)

    def render_thematic_break(self, token: block_token.ThematicBreak) -> str:
        content = "".join((self.indent(), token.tag)) # token.tag includes the newline
        self.is_at_beginning_of_line = True
        return content

    def render_html_block(self, token: block_token.HTMLBlock) -> str:
        lines = token.content[:-1].split("\n")
        return self.indent_lines(lines)

    def render_link_reference_definition_block(self, token: LinkReferenceDefinitionBlock) -> str:
        return self.render_inner(token)

    def render_link_reference_definition(self, token: LinkReferenceDefinition) -> str:
        if token.dest_type == "angle_uri":
            dest_part = "".join(("<", token.dest, ">"))
        else:
            dest_part = token.dest
        if len(token.title) > 0:
            closer = ')' if token.title_tag == '(' else token.title_tag
            title_part = " {}{}{}".format(token.title_tag, token.title, closer)
        else:
            title_part = ""
        content = "{}[{}]: {}{}\n".format(self.indent(), token.label, dest_part, title_part)
        self.is_at_beginning_of_line = True
        return content

    def render_blank_line(self, token: BlankLine) -> str:
        self.blank_line_emitted = True
        return "\n" # blank lines should not be indented
