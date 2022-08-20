from itertools import chain
import re
from mistletoe.base_renderer import BaseRenderer
from mistletoe import block_token, span_token

class BlankLine(block_token.BlockToken):
    pattern = re.compile(r'\s*\n$')

    def __init__(self, _):
        pass

    @classmethod
    def start(cls, line):
        return cls.pattern.match(line)

    @classmethod
    def read(cls, lines):
        return [next(lines)]

class MarkdownRenderer(BaseRenderer):
    def __init__(self, *extras):
        super().__init__(*chain((block_token.HTMLBlock, span_token.HTMLSpan, BlankLine), extras))
        self.render_map["SetextHeading"] = self.render_setext_heading
        self.render_map["CodeFence"] = self.render_fenced_code_block
        self.indentation = ""
        self.line_break_emitted = False

    def indent(self):
        if self.line_break_emitted:
            self.line_break_emitted = False
            return self.indentation
        else:
            return ""

    # span/inline tokens

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
        if len(token.title) > 0:
            opener = token.title_tag
            closer = ')' if token.title_tag == '(' else token.title_tag
            return "{}{}[{}]({} {}{}{})".format(self.indent(), prefix, self.render_inner(token), target, opener, token.title, closer)
        else:
            return "{}{}[{}]({})".format(self.indent(), prefix, self.render_inner(token), target)

    def render_auto_link(self, token: span_token.AutoLink) -> str:
        return "".join((self.indent(), "<", self.render_inner(token), ">"))

    def render_escape_sequence(self, token: span_token.EscapeSequence) -> str:
        return "".join((self.indent(), "\\", self.render_inner(token)))

    def render_line_break(self, token: span_token.LineBreak) -> str:
        content = "".join((self.indent(), token.tag, "\n"))
        self.line_break_emitted = True
        return content

    def render_html_span(self, token: span_token.HTMLSpan) -> str:
        return "".join((self.indent(), token.content))

    # block tokens

    def render_heading(self, token: block_token.Heading) -> str:
        content = "".join((self.indent(), "#" * token.level, " ", self.render_inner(token), " ", "#" * token.level, "\n"))
        self.line_break_emitted = True
        return content

    def render_setext_heading(self, token: block_token.SetextHeading) -> str:
        char = "=" if token.level == 1 else "-"
        content = "".join((self.indent(), self.render_inner(token), "\n", char * token.tag_length, "\n"))
        self.line_break_emitted = True
        return content

    # def render_quote(self, token: block_token.Quote) -> str:
    #     return self.render_inner(token)

    def render_paragraph(self, token: block_token.Paragraph) -> str:
        content = "".join((self.indent(), self.render_inner(token), "\n"))
        self.line_break_emitted = True
        return content

    def render_block_code(self, token: block_token.BlockCode) -> str:
        # remove the final endline before splitting into lines.
        lines = token.children[0].content[:-1].split("\n")
        prefix = self.indentation + "    "
        def process_line(line):
            return "".join((prefix, line, "\n"))
        content = "".join(map(process_line, lines))
        self.line_break_emitted = True
        return content

    def render_fenced_code_block(self, token: block_token.BlockCode) -> str:
        def make_lines():
            prefix = " " * token.indentation
            yield "".join((prefix, token.tag, token.info_string, "\n"))
            for line in token.children[0].content[:-1].split("\n"):
                yield "".join((prefix, line, "\n"))
            yield "".join((prefix, token.tag, "\n"))

        content = "".join(make_lines())
        self.line_break_emitted = True
        return content

    def render_list(self, token: block_token.List) -> str:
        return self.render_inner(token)

    def render_list_item(self, token: block_token.ListItem) -> str:
        prefix = "".join((self.indent(), token.leader, " "))
        prev_indentation = self.indentation
        self.indentation += " " * (len(token.leader) + 1)
        content = "".join((prefix, self.render_inner(token), "\n" if not self.line_break_emitted else ""))
        self.line_break_emitted = True
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
        self.line_break_emitted = True
        return content

    def render_html_block(self, token: block_token.HTMLBlock) -> str:
        content = "".join((self.indent(), token.content))
        self.line_break_emitted = True
        return content

    def render_blank_line(self, token: BlankLine) -> str:
        self.blank_line_emitted = True
        return "\n" # blank lines should not be indented
