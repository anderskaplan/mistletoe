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
        self.render_map['SetextHeading'] = self.render_setext_heading

    def render_strong(self, token: span_token.Strong) -> str:
        return "".join([token.tag * 2, self.render_inner(token), token.tag * 2])

    def render_emphasis(self, token: span_token.Emphasis) -> str:
        return "".join([token.tag, self.render_inner(token), token.tag])

    def render_inline_code(self, token: span_token.InlineCode) -> str:
        return "".join(['`', self.render_inner(token), '`'])

    def render_strikethrough(self, token: span_token.Strikethrough) -> str:
        return "".join(['~~', self.render_inner(token), '~~'])

    def render_image(self, token: span_token.Image) -> str:
        return self.render_image_or_link(token, '!', token.src)

    def render_link(self, token: span_token.Link) -> str:
        return self.render_image_or_link(token, '', token.target)

    def render_image_or_link(self, token, prefix, target):
        if len(token.title) > 0:
            opener = token.title_tag
            closer = ')' if token.title_tag == '(' else token.title_tag
            return "{}[{}]({} {}{}{})".format(prefix, self.render_inner(token), target, opener, token.title, closer)
        else:
            return "{}[{}]({})".format(prefix, self.render_inner(token), target)

    def render_auto_link(self, token: span_token.AutoLink) -> str:
        return "<{}>".format(self.render_inner(token))

    def render_escape_sequence(self, token: span_token.EscapeSequence) -> str:
        return "\\" + self.render_inner(token)

    def render_line_break(self, token: span_token.LineBreak) -> str:
        return token.tag + "\n"

    def render_heading(self, token: block_token.Heading) -> str:
        return "".join(["#" * token.level, " ", self.render_inner(token), " ", "#" * token.level, "\n"])

    def render_setext_heading(self, token: block_token.SetextHeading) -> str:
        char = "=" if token.level == 1 else "-"
        return self.render_inner(token) + "\n" + char * token.tag_length + "\n"

    # def render_quote(self, token: block_token.Quote) -> str:
    #     return self.render_inner(token)

    def render_paragraph(self, token: block_token.Paragraph) -> str:
        return self.render_inner(token) + "\n"

    # def render_block_code(self, token: block_token.BlockCode) -> str:
    #     return self.render_inner(token)

    # def render_list(self, token: block_token.List) -> str:
    #     return self.render_inner(token)

    # def render_list_item(self, token: block_token.ListItem) -> str:
    #     return self.render_inner(token)

    # def render_table(self, token: block_token.Table) -> str:
    #     return self.render_inner(token)

    # def render_table_cell(self, token: block_token.TableCell) -> str:
    #     return self.render_inner(token)

    # def render_table_row(self, token: block_token.TableRow) -> str:
    #     return self.render_inner(token)

    def render_thematic_break(self, token: block_token.ThematicBreak) -> str:
        return token.tag

    def render_html_block(self, token: block_token.HTMLBlock) -> str:
        return token.content

    def render_html_span(self, token: span_token.HTMLSpan) -> str:
        return token.content

    def render_blank_line(self, token: BlankLine) -> str:
        return "\n"
