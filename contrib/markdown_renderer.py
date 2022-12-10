"""
Markdown renderer for mistletoe.

This renderer is designed to make as "clean" a roundtrip as possible, markdown -> parsing -> rendering -> markdown,
except for nonessential whitespace.
"""

import os
import re
from itertools import chain, repeat
import sys
from typing import Iterable, Sequence

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

    Attributes:
        label (str): link label, used in link references.
        dest (str): link target.
        title (str): link title (default to empty).
        dest_type (str): "uri" for a plain uri, "angle_uri" for an uri within angle brackets.
        title_delimiter (str): the delimiter used for the title.
                               Single quote, double quote, or opening parenthesis.
    """
    repr_attributes = ("label", "dest", "title")

    def __init__(self, match):
        self.label, self.dest, self.title, self.dest_type, self.title_delimiter = match


class LinkReferenceDefinitionBlock(block_token.Footnote):
    """
    A sequence of "link reference definitions".
    This is a container block token. Its children are link reference definition tokens.

    This class inherits from Footnote and modifies the behavior of the constructor, so
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

    def span_to_lines(self, tokens: Iterable[span_token.SpanToken]) -> Iterable[str]:
        """
        Render a sequence of span (inline) tokens into a sequence of lines.
        """
        current_line = []
        for rendered_items in map(self.render, tokens):
            for w in rendered_items:
                if isinstance(w, span_token.LineBreak):
                    current_line.append(w.marker)
                    yield "".join(current_line)
                    current_line = []
                else:
                    current_line.append(w)
        if len(current_line) > 0:
            yield "".join(current_line)

    def embed_span_content(self, leader: str, tokens: Iterable[span_token.SpanToken], trailer: str = None) -> Sequence:
        """
        Flatten the content tree given by `tokens` into a list and append a leader and a trailer.
        The trailer defaults to the same as the leader.

        For example: the tokens (RawText('text'), Emphasis(RawText('Inner text')))
                     becomes [leader, 'text', '*', 'Inner text', '*', trailer]
        """
        content = [leader]
        for rendered_items in map(self.render, tokens):
            content.extend(rendered_items)
        content.append(trailer or leader)
        return content

    def block_to_lines(self, tokens: Iterable[block_token.BlockToken]) -> Iterable[str]:
        """
        Render a sequence of block tokens into a sequence of lines.
        """
        return chain.from_iterable(map(self.render, tokens))

    def prefix_lines(self, lines: Iterable[str], first_line_prefix: str, following_line_prefix: str = None) -> Iterable[str]:
        """
        Prepend a prefix string to a sequence of lines. The first line may have a different prefix
        from the following lines.
        """
        following_line_prefix = following_line_prefix or first_line_prefix
        isFirstLine = True
        for line in lines:
            if isFirstLine:
                l = first_line_prefix + line
                isFirstLine = False
            else:
                l = following_line_prefix + line
            yield l if not l.isspace() else ""

    def table_row_to_text(self, row) -> Sequence[str]:
        """
        Render each table cell on a table row to text.
        """
        return [next(self.span_to_lines(col.children)) for col in row.children]

    def calculate_table_column_widths(self, col_text) -> Sequence[int]:
        """
        Calculate column widths for a table.
        """
        MINIMUM_COLUMN_WIDTH = 3
        col_widths = []
        for row in col_text:
            while len(col_widths) < len(row):
                col_widths.append(MINIMUM_COLUMN_WIDTH)
            for index, text in enumerate(row):
                col_widths[index] = max(col_widths[index], len(text))
        return col_widths

    def table_separator_line_to_text(self, col_widths, col_align) -> Sequence[str]:
        """
        Create the text for the line separating header from contents in a table
        given column widths and alignments.

        Note: uses dashes for left justified columns, not a colon followed by dashes.
        """
        separator_text = []
        for index, width in enumerate(col_widths):
            align = col_align[index] if index < len(col_align) else None
            sep = ":" if align == 0 else "-"
            sep += "-" * (width - 2)
            sep += ":" if align == 0 or align == 1 else "-"
            separator_text.append(sep)
        return separator_text

    def table_row_to_line(self, col_text, col_widths, col_align) -> str:
        """
        Pad/align the text for a table row and add the borders (pipe characters).
        """
        padded_text = []
        for index, width in enumerate(col_widths):
            text = col_text[index] if index < len(col_text) else ""
            align = col_align[index] if index < len(col_align) else None
            if align is None:
                padded_text.append("{0: <{w}}".format(text, w=width))
            elif align == 0:
                padded_text.append("{0: ^{w}}".format(text, w=width))
            else:
                padded_text.append("{0: >{w}}".format(text, w=width))
        return "".join(("| ", " | ".join(padded_text), " |"))

    # span/inline tokens
    # rendered into lists of strings and LineBreak tokens.

    def render_raw_text(self, token: span_token.RawText) -> Sequence:
        return [token.content]

    def render_strong(self, token: span_token.Strong) -> Sequence:
        return self.embed_span_content(token.delimiter * 2, token.children)

    def render_emphasis(self, token: span_token.Emphasis) -> Sequence:
        return self.embed_span_content(token.delimiter, token.children)

    def render_inline_code(self, token: span_token.InlineCode) -> Sequence:
        return [token.delimiter, token.raw_content, token.delimiter]

    def render_strikethrough(self, token: span_token.Strikethrough) -> Sequence:
        return self.embed_span_content('~~', token.children)

    def render_image(self, token: span_token.Image) -> Sequence:
        return self.render_image_or_link(token, True, token.src)

    def render_link(self, token: span_token.Link) -> Sequence:
        return self.render_image_or_link(token, False, token.target)

    def render_image_or_link(self, token, isImage, target) -> Sequence:
        prefix = "![" if isImage else "["
        if token.dest_type == "uri" or token.dest_type == "angle_uri":
            dest_part = "".join(("<", target, ">")) if token.dest_type == "angle_uri" else target
            if len(token.title) > 0:
                # "![" description "](" dest_part " " title ")"
                closer = ')' if token.title_delimiter == '(' else token.title_delimiter
                return self.embed_span_content(
                    prefix,
                    token.children,
                    "]({} {}{}{})".format(dest_part, token.title_delimiter, token.title, closer))
            else:
                # "![" description "](" dest_part ")"
                return self.embed_span_content(prefix, token.children, "](" + dest_part + ")")
        elif token.dest_type == "full":
            # "![" description "][" label "]"
            return self.embed_span_content(prefix, token.children, "][" + token.label + "]")
        elif token.dest_type == "collapsed":
            # "![" description "][]"
            return self.embed_span_content(prefix, token.children, "][]")
        else:
            # "![" description "]"
            return self.embed_span_content(prefix, token.children, "]")

    def render_auto_link(self, token: span_token.AutoLink) -> Sequence:
        return self.embed_span_content('<', token.children, '>')

    def render_escape_sequence(self, token: span_token.EscapeSequence) -> Sequence:
        return ["\\" + token.children[0].content]

    def render_line_break(self, token: span_token.LineBreak) -> Sequence:
        return [token]

    def render_html_span(self, token: span_token.HTMLSpan) -> Sequence:
        return [token.content]

    # block tokens
    # rendered into sequences of lines (strings), to be joined by newlines.
    # except render_document, which returns a single string containing the fully rendered document.

    def render_document(self, token: block_token.Document) -> str:
        lines = self.block_to_lines(token.children)
        return "".join(chain.from_iterable(zip(lines, repeat("\n"))))

    def render_heading(self, token: block_token.Heading) -> Iterable[str]:
        items = ["#" * token.level]
        content = next(self.span_to_lines(token.children), "")
        if len(content) > 0:
            items.append(content)
        if len(token.closing_sequence) > 0:
            items.append(token.closing_sequence)
        return [" ".join(items)]

    def render_setext_heading(self, token: block_token.SetextHeading) -> Iterable[str]:
        content = list(self.span_to_lines(token.children))
        underline_char = "=" if token.level == 1 else "-"
        content.append(underline_char * token.underline_length)
        return content

    def render_quote(self, token: block_token.Quote) -> Iterable[str]:
        lines = list(self.block_to_lines(token.children))
        if len(lines) == 0:
            lines = [""]
        return self.prefix_lines(lines, "> ")

    def render_paragraph(self, token: block_token.Paragraph) -> Iterable[str]:
        return self.span_to_lines(token.children)

    def render_block_code(self, token: block_token.BlockCode) -> Iterable[str]:
        lines = token.children[0].content[:-1].split("\n")
        return self.prefix_lines(lines, "    ")

    def render_fenced_code_block(self, token: block_token.BlockCode) -> Iterable[str]:
        lines = ["".join((token.delimiter, token.info_string))]
        lines.extend(token.children[0].content[:-1].split("\n"))
        lines.append(token.delimiter)
        return self.prefix_lines(lines, " " * token.indentation)

    def render_list(self, token: block_token.List) -> Iterable[str]:
        return self.block_to_lines(token.children)

    def render_list_item(self, token: block_token.ListItem) -> Iterable[str]:
        lines = list(self.block_to_lines(token.children))
        if len(lines) == 0:
            lines = [""]
        return self.prefix_lines(lines, token.leader + " ", " " * (len(token.leader) + 1))

    def render_table(self, token: block_token.Table) -> Iterable[str]:
        # note: column widths are not preserved; they are automatically adjusted to fit the contents.
        content = [self.table_row_to_text(token.header), []]
        content.extend(self.table_row_to_text(row) for row in token.children)
        col_widths = self.calculate_table_column_widths(content)
        content[1] = self.table_separator_line_to_text(col_widths, token.column_align)
        return [self.table_row_to_line(col_text, col_widths, token.column_align) for col_text in content]

    def render_thematic_break(self, token: block_token.ThematicBreak) -> Iterable[str]:
        return [token.line]

    def render_html_block(self, token: block_token.HTMLBlock) -> Iterable[str]:
        lines = token.content[:-1].split("\n")
        return lines

    def render_link_reference_definition_block(self, token: LinkReferenceDefinitionBlock) -> Iterable[str]:
        return self.block_to_lines(token.children)

    def render_link_reference_definition(self, token: LinkReferenceDefinition) -> Iterable[str]:
        if token.dest_type == "angle_uri":
            dest_part = "".join(("<", token.dest, ">"))
        else:
            dest_part = token.dest
        if len(token.title) > 0:
            closer = ')' if token.title_delimiter == '(' else token.title_delimiter
            title_part = " {}{}{}".format(token.title_delimiter, token.title, closer)
        else:
            title_part = ""
        content = "[{}]: {}{}".format(token.label, dest_part, title_part)
        return [content]

    def render_blank_line(self, token: BlankLine) -> Iterable[str]:
        return [""]


def main():
    if len(sys.argv) != 3:
        print("Usage: {} <input file name> <output file name>".format(os.path.basename(__file__)))
        print("Parses the input markdown file and writes the output markdown file.")
        return -1

    with open(sys.argv[1], 'r', encoding='utf-8') as file:
        input = file.readlines()
    with MarkdownRenderer() as renderer:
        rendered = renderer.render(block_token.Document(input))
    with open(sys.argv[2], 'w', encoding='utf-8') as outf:
        outf.write(rendered)
    return 0


if __name__ == '__main__':
    sys.exit(main())
