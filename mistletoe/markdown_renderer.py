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

from mistletoe import block_token, span_token, token
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


class LinkReferenceDefinition(span_token.SpanToken):
    """
    Link reference definition. ([label]: dest "title")

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
    A sequence of link reference definitions.
    This is a container block token. Its children are link reference definition tokens.

    This class inherits from Footnote and modifies the behavior of the constructor,
    to keep the tokens in the AST.
    """
    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj.__init__(*args, **kwargs)
        return obj

    def __init__(self, matches):
        self.children = list(map(LinkReferenceDefinition, matches))


class Particle:
    def __init__(self, text: str, token: span_token.SpanToken, tag: str = None, wordwrap: bool = False):
        self.text = text
        self.token = token
        self.tag = tag
        self.wordwrap = wordwrap


class MarkdownRenderer(BaseRenderer):
    """
    Markdown renderer.
    """

    _whitespace = re.compile(r"\s+")

    def __init__(self, *extras):
        block_token.remove_token(block_token.Footnote)
        super().__init__(*chain((block_token.HTMLBlock, span_token.HTMLSpan, BlankLine, LinkReferenceDefinitionBlock), extras))
        self.render_map["SetextHeading"] = self.render_setext_heading
        self.render_map["CodeFence"] = self.render_fenced_code_block
        self.render_map["LinkReferenceDefinition"] = self.render_link_reference_definition

    def render(self, token: token.Token, max_line_length: int = None) -> str:
        """
        Renders the tree of tokens rooted at the given token into markdown.

        If `max_line_length` is specified, the document is word wrapped to the
        specified line length. Otherwise the formatting from the original (parsed)
        document is retained as much as possible.
        """
        if isinstance(token, block_token.BlockToken):
            lines = self.render_map[token.__class__.__name__](token, max_line_length=max_line_length)
        else:
            lines = self.span_to_lines([token], max_line_length=max_line_length)

        return "".join(map(lambda line: line + "\n", lines))

    # rendering of span/inline tokens.
    # rendered into sequences of Particles.

    def render_raw_text(self, token) -> Iterable[Particle]:
        yield Particle(token.content, token, wordwrap=True)

    def render_strong(self, token: span_token.Strong) -> Iterable[Particle]:
        return self.embed_span(Particle(token.delimiter * 2, token), token.children)

    def render_emphasis(self, token: span_token.Emphasis) -> Iterable[Particle]:
        return self.embed_span(Particle(token.delimiter, token), token.children)

    def render_inline_code(self, token: span_token.InlineCode) -> Iterable[Particle]:
        yield from (
            Particle(token.delimiter, token),
            Particle(token.raw_content, token),
            Particle(token.delimiter, token)
        )

    def render_strikethrough(self, token: span_token.Strikethrough) -> Iterable[Particle]:
        return self.embed_span(Particle('~~', token), token.children)

    def render_image(self, token: span_token.Image) -> Iterable[Particle]:
        return self.render_link_or_image(token, token.src, is_image=True)

    def render_link(self, token: span_token.Link) -> Iterable[Particle]:
        return self.render_link_or_image(token, token.target)

    def render_auto_link(self, token: span_token.AutoLink) -> Iterable[Particle]:
        yield Particle("<" + token.children[0].content + ">", token)

    def render_escape_sequence(self, token: span_token.EscapeSequence) -> Iterable[Particle]:
        yield Particle("\\" + token.children[0].content, token)

    def render_line_break(self, token: span_token.LineBreak) -> Iterable[Particle]:
        yield Particle(token.marker + "\n", token, wordwrap=token.soft)

    def render_html_span(self, token: span_token.HTMLSpan) -> Iterable[Particle]:
        yield Particle(token.content, token)

    def render_link_reference_definition(self, token: LinkReferenceDefinition) -> Iterable[Particle]:
        yield from (
            Particle("[", token),
            Particle(token.label, token, "label", wordwrap=True),
            Particle("]: ", token, wordwrap=True),
            Particle("<" + token.dest + ">" if token.dest_type == "angle_uri" else token.dest, token),
        )
        if token.title:
            yield from (
                Particle(" ", token, wordwrap=True),
                Particle(token.title_delimiter, token),
                Particle(token.title, token, wordwrap=True),
                Particle(')' if token.title_delimiter == '(' else token.title_delimiter, token),
            )

    # rendering of block tokens.
    # rendered into sequences of lines (strings), to be joined by newlines.

    def render_document(self, token: block_token.Document, max_line_length: int = None) -> Iterable[str]:
        return self.blocks_to_lines(token.children, max_line_length=max_line_length)

    def render_heading(self, token: block_token.Heading, max_line_length: int = None) -> Iterable[str]:
        # note: atx headings always fit on a single line
        line = "#" * token.level
        text = next(self.span_to_lines(token.children), "")
        if text:
            line += " " + text
        if token.closing_sequence:
            line += " " + token.closing_sequence
        return [line]

    def render_setext_heading(self, token: block_token.SetextHeading, max_line_length: int = None) -> Iterable[str]:
        yield from self.span_to_lines(token.children, max_line_length=max_line_length)
        underline_char = "=" if token.level == 1 else "-"
        yield underline_char * token.underline_length

    def render_quote(self, token: block_token.Quote, max_line_length: int = None) -> Iterable[str]:
        max_child_line_length = max_line_length - 2 if max_line_length else None
        lines = self.blocks_to_lines(token.children, max_line_length=max_child_line_length)
        return self.prefix_lines(lines or [""], "> ")

    def render_paragraph(self, token: block_token.Paragraph, max_line_length: int = None) -> Iterable[str]:
        return self.span_to_lines(token.children, max_line_length=max_line_length)

    def render_block_code(self, token: block_token.BlockCode, max_line_length: int = None) -> Iterable[str]:
        # TODO use content property
        lines = token.children[0].content[:-1].split("\n")
        return self.prefix_lines(lines, "    ")

    def render_fenced_code_block(self, token: block_token.BlockCode, max_line_length: int = None) -> Iterable[str]:
        # TODO use content property
        indentation = " " * token.indentation
        yield indentation + token.delimiter + token.info_string
        yield from self.prefix_lines(token.children[0].content[:-1].split("\n"), indentation)
        yield indentation + token.delimiter

    def render_list(self, token: block_token.List, max_line_length: int = None) -> Iterable[str]:
        return self.blocks_to_lines(token.children, max_line_length=max_line_length)

    def render_list_item(self, token: block_token.ListItem, max_line_length: int = None) -> Iterable[str]:
        indentation = len(token.leader) + 1
        max_child_line_length = max_line_length - indentation if max_line_length else None
        lines = self.blocks_to_lines(token.children, max_line_length=max_child_line_length)
        return self.prefix_lines(list(lines) or [""], token.leader + " ", " " * indentation)

    def render_table(self, token: block_token.Table, max_line_length: int = None) -> Iterable[str]:
        # note: column widths are not preserved; they are automatically adjusted to fit the contents.
        content = [self.table_row_to_text(token.header), []]
        content.extend(self.table_row_to_text(row) for row in token.children)
        col_widths = self.calculate_table_column_widths(content)
        content[1] = self.table_separator_line_to_text(col_widths, token.column_align)
        return [self.table_row_to_line(col_text, col_widths, token.column_align) for col_text in content]

    def render_thematic_break(self, token: block_token.ThematicBreak, max_line_length: int = None) -> Iterable[str]:
        return [token.line]

    def render_html_block(self, token: block_token.HTMLBlock, max_line_length: int = None) -> Iterable[str]:
        return token.content.split("\n")

    def render_link_reference_definition_block(self, token: LinkReferenceDefinitionBlock, max_line_length: int = None) -> Iterable[str]:
        # each link reference definition starts on a new line
        for child in token.children:
            yield from self.span_to_lines([child], max_line_length=max_line_length)

    def render_blank_line(self, token: BlankLine, max_line_length: int = None) -> Iterable[str]:
        return [""]

    # helper methods

    def blocks_to_lines(self, tokens: Iterable[block_token.BlockToken], max_line_length: int = None) -> Iterable[str]:
        """
        Renders a sequence of block tokens into a sequence of lines.
        """
        for token in tokens:
            yield from self.render_map[token.__class__.__name__](token, max_line_length=max_line_length)

    def span_to_lines(self, tokens: Iterable[span_token.SpanToken], max_line_length: int = None) -> Iterable[str]:
        """
        Renders a sequence of span (inline) tokens into a sequence of lines.
        """
        particles = chain.from_iterable(
            [self.render_map[token.__class__.__name__](token) for token in tokens]
        )
        current_line = ""
        if not max_line_length:
            # plain rendering: merge all particles and split on newlines
            for particle in particles:
                if "\n" in particle.text:
                    lines = particle.text.split("\n")
                    yield current_line + lines[0]
                    for inner_line in lines[1:-2]:
                        yield inner_line
                    current_line = lines[-1]
                else:
                    current_line += particle.text
        else:
            # render with word wrapping
            for word in self.make_words(particles):
                if word == "\n":
                    # hard line break
                    yield current_line
                    current_line = ""
                    continue

                if not current_line:
                    # first word on an empty line: accept and continue
                    current_line = word
                    continue

                # try to fit the word on the current line.
                # if it doesn't fit, flush the line and start on the next
                test = current_line + " " + word
                if len(test) <= max_line_length:
                    current_line = test
                else:
                    yield current_line
                    current_line = word

        if current_line:
            yield current_line

    @classmethod
    def make_words(cls, particles: Iterable[Particle]) -> Iterable[str]:
        """
        Aggregates and splits a sequence of Particles into words, which do not contain breakable spaces or line breaks.
        The exception is hard line breaks which are represented by a single newline character.
        """
        word = ""
        for particle in particles:
            if particle.wordwrap:
                first = True
                for item in cls._whitespace.split(particle.text):
                    if first:
                        word += item
                        first = False
                    else:
                        if word:
                            yield word
                        word = item
            elif isinstance(particle.token, span_token.LineBreak) and not particle.token.soft:
                yield from (word + particle.text[:-1], "\n")
                word = ""
            else:
                word += particle.text

        if word:
            yield word

    @classmethod
    def prefix_lines(cls, lines: Iterable[str], first_line_prefix: str, following_line_prefix: str = None) -> Iterable[str]:
        """
        Prepend a prefix string to a sequence of lines. The first line may have a different prefix
        from the following lines.
        """
        following_line_prefix = following_line_prefix or first_line_prefix
        is_first_line = True
        for line in lines:
            if is_first_line:
                l = first_line_prefix + line
                is_first_line = False
            else:
                l = following_line_prefix + line
            yield l if not l.isspace() else ""

    def table_row_to_text(self, row) -> Sequence[str]:
        """
        Render each table cell on a table row to text.
        """
        return [next(self.span_to_lines(col.children), "") for col in row.children]

    @classmethod
    def calculate_table_column_widths(cls, col_text) -> Sequence[int]:
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

    @classmethod
    def table_separator_line_to_text(cls, col_widths, col_align) -> Sequence[str]:
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

    @classmethod
    def table_row_to_line(cls, col_text, col_widths, col_align) -> str:
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

    def embed_span(self, leader: Particle, tokens: Iterable[span_token.SpanToken], trailer: Particle = None) -> Iterable[Particle]:
        """
        Flattens `tokens` and embeds within a leader and a trailer.
        The trailer defaults to the same as the leader.
        """
        yield leader
        for token in tokens:
            yield from self.render_map[token.__class__.__name__](token)
        yield trailer or leader

    def render_link_or_image(self, token: span_token.SpanToken, target: str, is_image: bool=False) -> Iterable[Particle]:
        yield from self.embed_span(
            Particle("![" if is_image else "[", token),
            token.children,
            Particle("]", token)
        )

        if token.dest_type == "uri" or token.dest_type == "angle_uri":
            # "![" description "](" dest_part [" " title] ")"
            yield Particle("(", token)
            dest_part = "<" + target + ">" if token.dest_type == "angle_uri" else target
            yield Particle(dest_part, token, "dest_part")
            if token.title:
                yield from (
                    Particle(" ", token, wordwrap=True),
                    Particle(token.title_delimiter, token),
                    Particle(token.title, token, "title", wordwrap=True),
                    Particle(')' if token.title_delimiter == '(' else token.title_delimiter, token)
                )
            yield Particle(")", token)
        elif token.dest_type == "full":
            # "![" description "][" label "]"
            yield from (
                Particle("[", token),
                Particle(token.label, token, "label", wordwrap=True),
                Particle("]", token)
            )
        elif token.dest_type == "collapsed":
            # "![" description "][]"
            yield Particle("[]", token)
        else:
            # "![" description "]"
            pass


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
